"""V2 graph-driven multi-agent coordination runtime.

The runtime deliberately keeps GoldGraph and hidden tests outside the agent workspace.
Observed edges are created only from task file-read events and declared artifact provenance.
"""
from __future__ import annotations
import argparse, concurrent.futures, hashlib, json, os, shutil, subprocess, tempfile, threading, time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable
from openai import OpenAI

# DeepSeek billing ledger used by the frozen runs: cached input, uncached input,
# and output prices in USD per million tokens.  The second tuple entry records
# the alternate price tier retained in the ledger schema; the runner uses the
# first entry consistently for this experiment.
RATES=((0.003,0.006),(0.15,0.30),(0.60,1.20))
SYSTEM_PROMPT=("You are one coding agent in a concurrent repository workflow. Inspect files before editing. "
              "Implement the requested artifact using the contract version you read, copying the semantic behavior into your own code. "
              "Do not import or call semkg_contract at runtime; the artifact must preserve the assumption it used. "
              "Use only the supplied tools and keep changes inside your attempt directory. Do not run repository-wide tests or explore unrelated files; after required reads, write the requested output immediately.")
TASKS=("A_direct","B_transitive","D_unrelated","E_unrelated")
AFFECTED_TRUE={"A_direct","B_transitive"}
UNRELATED={"D_unrelated","E_unrelated"}

@dataclass
class TaskSpec:
    task_id:str
    role:str
    output_files:list[str]
    prompt:str
    direct_contract_read:bool=False
    upstream:list[str]=field(default_factory=list)

@dataclass
class TaskState:
    task_id:str
    state:str="READY"
    attempt_id:str=""
    assumption_versions:dict[str,int]=field(default_factory=dict)
    observed_reads:list[str]=field(default_factory=list)
    upstream_provenance:dict[str,str]=field(default_factory=dict)
    invalidation_reason:str|None=None
    start:float|None=None
    end:float|None=None
    committed_sha:str|None=None

class EventLog:
    def __init__(self): self.events=[]; self.lock=threading.Lock()
    def emit(self,kind:str,**data):
        ev={"kind":kind,"t_monotonic":time.perf_counter(),**data}
        with self.lock: self.events.append(ev)
        return ev
    def snapshot(self):
        with self.lock: return list(self.events)

class ObservedGraph:
    def __init__(self): self.edges=[]; self.sources=[]
    def add(self,src:str,relation:str,dst:str,source:str,detail:str):
        item={"src":src,"relation":relation,"dst":dst,"source":source,"detail":detail}
        if item not in self.edges: self.edges.append(item)
    def from_events(self,events):
        for e in events:
            if e["kind"]=="contract_read" and e.get("version") is not None:
                self.add("contract:C","reads",e["task_id"],"runtime_file_read",e["path"])
            elif e["kind"]=="artifact_read":
                self.add(e["upstream_task"],"artifact_to_task",e["task_id"],"runtime_file_read",e["path"])
        self.edges.sort(key=lambda x:(x["src"],x["relation"],x["dst"],x["source"],x["detail"]))
    def affected(self,contract_node="contract:C"):
        adj={}
        for e in self.edges: adj.setdefault(e["src"],[]).append(e["dst"])
        seen=set(); stack=[contract_node]
        trace=[]
        while stack:
            n=stack.pop()
            for nxt in sorted(adj.get(n,[])):
                trace.append({"from":n,"to":nxt})
                if nxt not in seen: seen.add(nxt); stack.append(nxt)
        return seen,trace
    def direct_readers(self): return {e["dst"] for e in self.edges if e["src"]=="contract:C" and e["relation"]=="reads"}

class CoordinationPolicy:
    name="base"
    def select(self,graph:ObservedGraph,states:dict[str,TaskState],mutation:dict[str,Any])->tuple[set[str],dict[str,Any]]:
        raise NotImplementedError
class StaticDAGPolicy(CoordinationPolicy):
    name="StaticDAG"
    def select(self,graph,states,mutation): return set(),{"mode":"explicit_dag_only","graph_called":False}
class VersionCheckPolicy(CoordinationPolicy):
    name="Version-Check"
    def select(self,graph,states,mutation):
        selected=graph.direct_readers()
        return selected,{"mode":"direct_observed_reads","graph_called":True,"direct_readers":sorted(selected)}
class GlobalInvalidatePolicy(CoordinationPolicy):
    name="Global-Invalidate"
    def select(self,graph,states,mutation):
        selected=set(states)
        return selected,{"mode":"declared_scope_all_tasks","graph_called":False}
class SemKGNoPropagationPolicy(CoordinationPolicy):
    name="SemKG-w/o-Graph"
    def select(self,graph,states,mutation):
        selected=graph.direct_readers()
        return selected,{"mode":"ablation_no_transitive_propagation","graph_called":True,"direct_readers":sorted(selected),"traversal":[]}
class SemKGObservedPolicy(CoordinationPolicy):
    name="SemKG-Observed"
    def select(self,graph,states,mutation):
        selected,trace=graph.affected()
        return selected,{"mode":"observed_graph_traversal","graph_called":True,"traversal":trace,"edges":list(graph.edges)}
POLICIES={p.name:p for p in [StaticDAGPolicy(),VersionCheckPolicy(),GlobalInvalidatePolicy(),SemKGNoPropagationPolicy(),SemKGObservedPolicy()]}

def _usage(u):
    d=u.model_dump() if hasattr(u,"model_dump") else dict(u or {})
    return {k:int(v) for k,v in d.items() if isinstance(v,(int,float))}
def _cost(u):
    hit=u.get("prompt_cache_hit_tokens",0); miss=u.get("prompt_cache_miss_tokens",max(0,u.get("prompt_tokens",0)-hit)); out=u.get("completion_tokens",0)
    return (hit*RATES[0][0]+miss*RATES[1][0]+out*RATES[2][0])/1e6

def safe(root:Path,raw:str):
    p=Path(raw)
    if p.is_absolute() or ".." in p.parts: raise ValueError("unsafe path")
    q=(root/p).resolve()
    if root.resolve() not in q.parents and q!=root.resolve(): raise ValueError("path escape")
    return q

def agent(root:Path,task:TaskSpec,attempt_root:Path,events:EventLog,version:int,max_turns=16):
    client=OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"],base_url="https://api.deepseek.com",timeout=90,max_retries=0)
    system=SYSTEM_PROMPT
    prompt=(task.prompt+f"\nYour task id is {task.task_id}. The attempt directory is {attempt_root.name}. "
            "Write all outputs under that directory using relative paths. You may read committed upstream artifacts. "
            "Run a small local check if useful, then report exactly what you wrote.")
    msgs=[{"role":"system","content":system},{"role":"user","content":prompt}]; trace=[]; total=0.0; started=time.perf_counter(); events.emit("agent_start",task_id=task.task_id,attempt_id=attempt_root.name,version=version)
    for turn in range(max_turns):
        r=client.chat.completions.create(model=os.environ.get("DEEPSEEK_MODEL","deepseek-flash"),messages=msgs,tools=TOOLS,max_tokens=900,stream=False,extra_body={"thinking":{"type":"disabled"}})
        u=_usage(r.usage); c=_cost(u); total+=c; m=r.choices[0].message
        rec={"turn":turn+1,"usage":u,"cost_usd":c,"tools":[]}; trace.append(rec); msgs.append(m.model_dump(exclude_none=True))
        if not m.tool_calls:
            events.emit("agent_message",task_id=task.task_id,attempt_id=attempt_root.name,message=(m.content or "")[-1000:]); break
        for call in m.tool_calls:
            name=call.function.name; rec["tools"].append(name); out={"ok":False}
            try:
                args=json.loads(call.function.arguments)
                if name=="read_file":
                    raw=args["path"]; q=safe(root,raw); content=q.read_text(encoding="utf-8")[:12000]
                    norm=raw.replace('\\','/')
                    events.emit("file_read",task_id=task.task_id,attempt_id=attempt_root.name,path=norm)
                    if norm.endswith("semkg_contract.py"):
                        events.emit("contract_read",task_id=task.task_id,attempt_id=attempt_root.name,path=norm,version=version)
                    if task.task_id=="B_transitive" and norm.endswith("producer.py"):
                        events.emit("artifact_read",task_id=task.task_id,attempt_id=attempt_root.name,upstream_task="A_direct",path=norm)
                    out={"ok":True,"content":content}
                elif name=="write_file":
                    raw=args["path"].replace("\\","/"); prefix=attempt_root.name+"/"
                    rel=raw[len(prefix):] if raw.startswith(prefix) else raw
                    q=safe(attempt_root,rel); q.parent.mkdir(parents=True,exist_ok=True); q.write_text(args["content"],encoding="utf-8"); events.emit("file_write",task_id=task.task_id,attempt_id=attempt_root.name,path=rel); out={"ok":True}
                elif name=="run_command":
                    cmd=args["command"]
                    if not cmd.startswith("python "): raise ValueError("only python commands allowed")
                    q=subprocess.run(cmd,cwd=root,shell=True,capture_output=True,text=True,timeout=60); out={"ok":q.returncode==0,"returncode":q.returncode,"stdout":q.stdout[-3000:],"stderr":q.stderr[-3000:]}
            except Exception as exc: out={"ok":False,"error":str(exc)}
            msgs.append({"role":"tool","tool_call_id":call.id,"content":json.dumps(out)})
    events.emit("agent_end",task_id=task.task_id,attempt_id=attempt_root.name,version=version,trace=trace)
    return {"task_id":task.task_id,"attempt_id":attempt_root.name,"trace":trace,"cost_usd":total,"started":started,"ended":time.perf_counter()}

TOOLS=[{"type":"function","function":{"name":"read_file","description":"Read a UTF-8 file in this workspace.","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},{"type":"function","function":{"name":"write_file","description":"Write a UTF-8 file under the attempt directory.","parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}}},{"type":"function","function":{"name":"run_command","description":"Run a Python check in the workspace.","parameters":{"type":"object","properties":{"command":{"type":"string"}},"required":["command"]}}}]

def contract_pair(scenario:str):
    if scenario=="price_unit":
        return ("CONTRACT_VERSION = 1\ndef normalize_price(value):\n    return float(value) / 100.0\n","CONTRACT_VERSION = 2\ndef normalize_price(value):\n    return float(value)\n",{"input":1234,"expected":1234.0,"old":12.34})
    if scenario=="api_error":
        return ("CONTRACT_VERSION = 1\ndef parse_error(response):\n    if 'error' not in response: return None\n    return response['error']\n","CONTRACT_VERSION = 2\nclass MissingError(Exception): pass\ndef parse_error(response):\n    if 'error' not in response: raise MissingError('missing error')\n    return response['error']\n",{"input":{},"expected":"MissingError","old":None})
    if scenario=="state_machine":
        return ("CONTRACT_VERSION = 1\ndef can_transition(old,new):\n    return (old,new) in {('new','paid'),('new','cancelled')}\n","CONTRACT_VERSION = 2\ndef can_transition(old,new):\n    return (old,new) in {('new','paid'),('new','cancelled'),('paid','refunded')}\n",{"input":("paid","refunded"),"expected":True,"old":False})
    if scenario=="idempotency":
        return ("CONTRACT_VERSION = 1\ndef idempotency_key(request):\n    return request['id']\n","CONTRACT_VERSION = 2\ndef idempotency_key(request):\n    return request['id'] + ':' + request.get('attempt','0')\n",{"input":{"id":"A","attempt":"2"},"expected":"A:2","old":"A"})
    return ("CONTRACT_VERSION = 1\nDEFAULT_TIMEOUT = 5\ndef timeout(config):\n    return config.get('timeout', DEFAULT_TIMEOUT)\n","CONTRACT_VERSION = 2\nDEFAULT_TIMEOUT = 30\ndef timeout(config):\n    return config.get('timeout', DEFAULT_TIMEOUT)\n",{"input":{},"expected":30,"old":5})


def topology_for(scenario:str):
    return {"price_unit":"direct_dependency","api_error":"three_node_chain","state_machine":"fork_dependency","idempotency":"join_dependency","configuration":"cross_module_dependency"}.get(scenario,"independent_parallel")

def task_specs(scenario):
    fn={"price_unit":"normalize_price","api_error":"parse_error","state_machine":"can_transition","idempotency":"idempotency_key","configuration":"timeout"}[scenario]
    arg={"price_unit":"1234","api_error":"{}","state_machine":"'paid', 'refunded'","idempotency":"{'id':'A','attempt':'2'}","configuration":"{}"}[scenario]
    a=(f"Read semkg_contract.py first. Create producer.py under the attempt directory. Define {fn}({arg}) behavior by copying the current contract semantics into producer.py; do not import semkg_contract. The v2 behavior must be implemented when you read version 2.")
    if scenario=="state_machine":
        b=("Immediately call read_file on semkg_contract.py and then write downstream.py. This is the fork branch: implement consume(old,new) by copying the current contract v1/v2 semantics into the artifact. Do not import semkg_contract; the required output is downstream.py.")
    else:
        b=("Immediately call read_file on committed/A_direct/producer.py. Then immediately call write_file with path downstream.py (or your attempt directory prefix) and create a downstream.py defining consume(value) by calling the producer function or equivalent copied implementation. Do not import semkg_contract; preserve the version observed in the upstream artifact. If you import the committed producer, use the package path `committed.A_direct.producer` or the file-relative path `../A_direct/producer.py`; never prefix `committed/` twice. The required output is downstream.py, not a prose answer.")
    d=("Your first tool call must be write_file with path unrelated_report.py (or your attempt directory prefix). Create a real deterministic report() returning a nonempty string containing D_unrelated. Do not read semkg_contract and do not create any other file.")
    e=("Your first tool call must be write_file with path unrelated_config.py (or your attempt directory prefix). Create a real deterministic feature_flag() returning True and CONFIG_NAME. Do not read semkg_contract and do not create any other file.")
    return [TaskSpec("A_direct","affected_direct",["producer.py"],a,True,[]),TaskSpec("B_transitive","affected_transitive",["downstream.py"],b,scenario!="state_machine",["A_direct"]),TaskSpec("D_unrelated","unrelated",["unrelated_report.py"],d,False,[]),TaskSpec("E_unrelated","unrelated",["unrelated_config.py"],e,False,[])]

def write_contract(root,scenario,v1):
    v1text,v2text,_=contract_pair(scenario); (root/"semkg_contract.py").write_text(v1text if v1 else v2text,encoding="utf-8"); return v1text,v2text

def commit_attempt(root,task,attempt):
    dest=root/"committed"/task.task_id; dest.mkdir(parents=True,exist_ok=True)
    hashes={}
    for f in task.output_files:
        src=attempt/f
        if src.exists():
            data=src.read_bytes(); (dest/f).write_bytes(data); hashes[f]=hashlib.sha256(data).hexdigest()
    return hashes

def evaluate(root,scenario):
    _,v2,meta=contract_pair(scenario); evalroot=root/"eval"; evalroot.mkdir(exist_ok=True)
    # evaluator copies committed artifacts and supplies an independent v2 oracle; it never reads agent messages.
    results={"affected":{},"unrelated":{},"oracle":meta}
    prod=root/"committed"/"A_direct"/"producer.py"; down=root/"committed"/"B_transitive"/"downstream.py"
    # Evaluate committed artifacts in a root-scoped import environment so that
    # a valid `committed.A_direct.producer` import is independent of the
    # controller's own working directory.  The evaluator still supplies the
    # v2 oracle and never reads agent messages or hidden labels.
    import sys
    old_cwd = os.getcwd()
    old_path = list(sys.path)
    os.chdir(root)
    sys.path.insert(0, str(root))
    try:
      if prod.exists():
        ns={"__file__":str(prod),"__name__":"artifact"}; exec(compile(prod.read_text(encoding="utf-8"),str(prod),"exec"),ns)
        fn={"price_unit":"normalize_price","api_error":"parse_error","state_machine":"can_transition","idempotency":"idempotency_key","configuration":"timeout"}[scenario]
        try:
            got=ns[fn](*meta["input"] if isinstance(meta["input"],tuple) else [meta["input"]]) if scenario=="state_machine" else ns[fn](meta["input"])
            results["affected"]["A_direct"]=(got==meta["expected"])
        except Exception as e: results["affected"]["A_direct"]=(meta["expected"]==e.__class__.__name__)
      else: results["affected"]["A_direct"]=False
      if down.exists():
        ns={"__file__":str(down),"__name__":"artifact"}; exec(compile(down.read_text(encoding="utf-8"),str(down),"exec"),ns)
        try:
            inp=meta["input"]
            got=ns["consume"](*inp) if scenario=="state_machine" else ns["consume"](inp)
            if isinstance(got,dict): got=got.get("normalized_price") if scenario=="price_unit" else got.get("accepted") if scenario=="state_machine" else got.get("value",got)
            results["affected"]["B_transitive"]=(got==meta["expected"])
        except Exception as e: results["affected"]["B_transitive"]=(meta["expected"]==e.__class__.__name__)
      else: results["affected"]["B_transitive"]=False
      for tid,fn in [("D_unrelated","report"),("E_unrelated","feature_flag")]:
        p=next((root/"committed"/tid).glob("*.py"),None)
        ok=False
        if p:
            ns={"__file__":str(p),"__name__":"artifact"}; exec(compile(p.read_text(encoding="utf-8"),str(p),"exec"),ns)
            try: ok=bool(ns[fn]())
            except Exception: ok=False
        results["unrelated"][tid]=ok
      results["all_pass"]=all(results["affected"].values()) and all(results["unrelated"].values())
      return results
    finally:
      os.chdir(old_cwd)
      sys.path[:] = old_path

def run_workflow(repo:Path,scenario:str,protocol:str,repeat:int,model=None):
    root=Path(tempfile.mkdtemp(prefix=f"semkg-v2-{protocol}-{scenario}-{repeat}-")); shutil.copytree(repo,root,dirs_exist_ok=True,ignore=shutil.ignore_patterns(".git","__pycache__","*.pyc"))
    events=EventLog(); specs={x.task_id:x for x in task_specs(scenario)}; states={tid:TaskState(tid) for tid in specs}; attempts={}; total_cost=0.0; wall_start=time.perf_counter()
    v1,v2=write_contract(root,scenario,True); events.emit("workflow_start",protocol=protocol,scenario=scenario,topology=topology_for(scenario),repo=repo.name,repeat=repeat)
    # Real concurrent first wave: A, D, E. B starts after A's first artifact is committed.
    def launch(tid,version=1):
        task=specs[tid]; aid=f"{tid}_attempt_{len(attempts.get(tid,[]))+1}"; ar=root/"attempts"/aid; ar.mkdir(parents=True,exist_ok=True); attempts.setdefault(tid,[]).append(aid); states[tid].attempt_id=aid; states[tid].state="RUNNING"; states[tid].assumption_versions={"C":version}; states[tid].start=time.perf_counter(); return agent(root,task,ar,events,version)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futs={tid:pool.submit(launch,tid,1) for tid in ["A_direct","D_unrelated","E_unrelated"]}
        # Wait for A to produce an artifact and its v1 read. This is a real event barrier, not a simulated tick.
        deadline=time.time()+90
        while time.time()<deadline:
            ev=events.snapshot()
            if any(e["kind"]=="contract_read" and e["task_id"]=="A_direct" and e["version"]==1 for e in ev) and any(e["kind"]=="file_write" and e["task_id"]=="A_direct" for e in ev): break
            time.sleep(.01)
        ares=futs["A_direct"].result(); total_cost+=ares["cost_usd"]; states["A_direct"].state="VERIFIED"; states["A_direct"].end=ares["ended"]; states["A_direct"].observed_reads=[e["path"] for e in events.snapshot() if e.get("task_id")=="A_direct" and e["kind"]=="contract_read"]; states["A_direct"].committed_sha=str(commit_attempt(root,specs["A_direct"],root/"attempts"/ares["attempt_id"]))
        events.emit("commit",task_id="A_direct",attempt_id=ares["attempt_id"],version=1); states["A_direct"].state="COMMITTED"
        bf=pool.submit(launch,"B_transitive",1)
        # Wait until B has read the v1 producer; then mutate the contract while D/E remain in flight when possible.
        deadline=time.time()+90
        while time.time()<deadline:
            ev=events.snapshot()
            if any(e["kind"]=="artifact_read" and e["task_id"]=="B_transitive" for e in ev) or (scenario=="state_machine" and any(e["kind"]=="contract_read" and e["task_id"]=="B_transitive" for e in ev)): break
            time.sleep(.01)
        events.emit("mutation_prepare",scenario=scenario,from_version=1,to_version=2)
        contract=root/"semkg_contract.py"; contract.write_text(v2,encoding="utf-8"); mutation={"event":"M1","from":1,"to":2,"time":time.perf_counter()}; events.emit("contract_mutation",**mutation)
        for tid,f in futs.items():
            if tid!="A_direct":
                r=f.result(); total_cost+=r["cost_usd"]; states[tid].end=r["ended"]; commit_attempt(root,specs[tid],root/"attempts"/r["attempt_id"]); states[tid].state="COMMITTED"; events.emit("commit",task_id=tid,attempt_id=r["attempt_id"],version=1)
        br=bf.result(); total_cost+=br["cost_usd"]; states["B_transitive"].end=br["ended"]
    graph=ObservedGraph(); graph.from_events(events.snapshot()); policy=POLICIES[protocol]; selected,decision=policy.select(graph,states,mutation); events.emit("graph_decision",protocol=protocol,selected=sorted(selected),decision=decision)
    # Mark stale attempts. The commit gate checks the mutation version before accepting them.
    for tid in selected:
        states[tid].state="INVALIDATED"; states[tid].invalidation_reason="contract:C v1->v2 via observed graph" if protocol=="SemKG-Observed" else decision["mode"]
    # B's first result is committed only for StaticDAG; otherwise its late result is discarded.
    if protocol=="StaticDAG":
        if br.get("attempt_id"): states["B_transitive"].state="COMMITTED"; commit_attempt(root,specs["B_transitive"],root/"attempts"/br["attempt_id"]); events.emit("commit",task_id="B_transitive",attempt_id=br["attempt_id"],version=1,stale=True)
    # Re-dispatch exactly selected tasks, and only those tasks. B waits on current producer for rework.
    rework=[]
    for tid in sorted(selected):
        if tid=="B_transitive":
            # ensure current producer is available after A rework
            pass
        if tid=="A_direct":
            ar=root/"attempts"/f"{tid}_attempt_{len(attempts[tid])+1}"; ar.mkdir(parents=True,exist_ok=True); rr=agent(root,specs[tid],ar,events,2); total_cost+=rr["cost_usd"]; commit_attempt(root,specs[tid],ar); states[tid].state="COMMITTED"; rework.append(tid); events.emit("requeue_commit",task_id=tid,attempt_id=ar.name,version=2)
    if "B_transitive" in selected:
        ar=root/"attempts"/f"B_transitive_attempt_{len(attempts['B_transitive'])+1}"; ar.mkdir(parents=True,exist_ok=True); rr=agent(root,specs["B_transitive"],ar,events,2); total_cost+=rr["cost_usd"]; commit_attempt(root,specs["B_transitive"],ar); states["B_transitive"].state="COMMITTED"; rework.append("B_transitive"); events.emit("requeue_commit",task_id="B_transitive",attempt_id=ar.name,version=2)
    # Global invalidation redoes unaffected tasks; Version-Check never redoes B unless it directly read C.
    for tid in sorted(selected-{"A_direct","B_transitive"}):
        ar=root/"attempts"/f"{tid}_attempt_{len(attempts[tid])+1}"; ar.mkdir(parents=True,exist_ok=True); rr=agent(root,specs[tid],ar,events,2); total_cost+=rr["cost_usd"]; commit_attempt(root,specs[tid],ar); states[tid].state="COMMITTED"; rework.append(tid); events.emit("requeue_commit",task_id=tid,attempt_id=ar.name,version=2)
    # Persist evaluator failures as auditable run records instead of letting the
    # queue lose the usage ledger accumulated by the Agent calls.  The error is
    # still a failed workflow; it is never converted into a hidden-test pass.
    try:
        ev=evaluate(root,scenario)
    except Exception as exc:
        ev={"all_pass":False,"error":f"{type(exc).__name__}: {exc}","affected":{},"unrelated":{},"oracle":contract_pair(scenario)[2]}
        events.emit("hidden_test_error",error=ev["error"])
    events.emit("hidden_test",result=ev)
    for tid,st in states.items():
        if st.state not in {"COMMITTED","INVALIDATED"}: st.state="FAILED"
    overlaps=[]; all_ev=events.snapshot(); starts={}; ends={}
    for e in all_ev:
        if e["kind"]=="agent_start": starts[e["task_id"]]=e["t_monotonic"]
        if e["kind"]=="agent_end": ends[e["task_id"]]=e["t_monotonic"]
    tids=list(starts)
    for i,a in enumerate(tids):
        for b in tids[i+1:]:
            if starts[a]<ends.get(b,starts[b]) and starts[b]<ends.get(a,starts[a]): overlaps.append([a,b])
    result={"schema":"semkg-v2-run-v1","repository":repo.name,"scenario":scenario,"topology":topology_for(scenario),"protocol":protocol,"repeat":repeat,"mutation":mutation,"tasks":{k:asdict(v) for k,v in states.items()},"observed_graph":{"edges":graph.edges},"decision_trace":decision,"selected_tasks":sorted(selected),"true_affected_tasks":sorted(AFFECTED_TRUE),"rework_tasks":sorted(rework),"events":all_ev,"overlapping_pairs":overlaps,"evaluation":ev,"total_cost_usd":total_cost,"makespan_seconds":time.perf_counter()-wall_start,"model":os.environ.get("DEEPSEEK_MODEL","deepseek-flash")}
    archive=Path("realworld_v2/artifacts")/f"{repo.name}_{scenario}_{protocol}_{repeat}"; archive.mkdir(parents=True,exist_ok=True)
    for part in ["committed","attempts","eval"]:
        src=root/part
        if src.exists(): shutil.copytree(src,archive/part,dirs_exist_ok=True,ignore=shutil.ignore_patterns("__pycache__","*.pyc"))
    shutil.copy2(root/"semkg_contract.py",archive/"semkg_contract.py")
    shutil.rmtree(root,ignore_errors=True); return result

def main():
 p=argparse.ArgumentParser(); p.add_argument('--repo',type=Path,required=True); p.add_argument('--scenario',required=True); p.add_argument('--protocol',required=True,choices=sorted(POLICIES)); p.add_argument('--repeat',type=int,default=0); p.add_argument('--out',type=Path,required=True); a=p.parse_args();
 if not os.environ.get('DEEPSEEK_API_KEY'): raise SystemExit('DEEPSEEK_API_KEY missing')
 r=run_workflow(a.repo,a.scenario,a.protocol,a.repeat); a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(r,indent=2),encoding='utf-8'); print(json.dumps({'protocol':a.protocol,'scenario':a.scenario,'pass':r['evaluation']['all_pass'],'selected':r['selected_tasks'],'rework':r['rework_tasks'],'cost':r['total_cost_usd']}))
if __name__=='__main__': main()








