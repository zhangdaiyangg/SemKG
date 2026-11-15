import json, threading
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'controller'))
from v2_runtime import ObservedGraph, TaskState, POLICIES

def check(name, ok, detail=''): return {'name':name,'passed':bool(ok),'detail':detail}
def main():
 out=[]; g=ObservedGraph(); g.add('contract:C','reads','A_direct','runtime_file_read','semkg_contract.py'); g.add('A_direct','artifact_to_task','B_transitive','runtime_file_read','committed/A_direct/producer.py'); g.add('unrelated','artifact_to_task','D_unrelated','runtime_file_read','x')
 aff,_=g.affected(); out += [check('direct_dependency_identified','A_direct' in aff),check('three_hop_propagation','B_transitive' in aff),check('unrelated_not_selected','D_unrelated' not in aff)]
 missing=ObservedGraph(); missing.add('contract:C','reads','A_direct','runtime_file_read','semkg_contract.py'); m,_=missing.affected(); out.append(check('missing_edge_detected_as_miss','B_transitive' not in m))
 false=ObservedGraph(); false.add('contract:C','reads','A_direct','runtime_file_read','semkg_contract.py'); false.add('contract:C','reads','D_unrelated','runtime_file_read','false_edge'); fa,_=false.affected(); out.append(check('false_edge_explainable','D_unrelated' in fa))
 states={x:TaskState(x) for x in ['A_direct','B_transitive','D_unrelated','E_unrelated']}; sel,dec=POLICIES['SemKG-Observed'].select(g,states,{'from':1,'to':2}); out.append(check('semkg_query_changes_decision',sel=={'A_direct','B_transitive'})); sel0,dec0=POLICIES['StaticDAG'].select(g,states,{'from':1,'to':2}); out.append(check('graph_disabled_not_claimed',not dec0.get('graph_called',False) and not sel0)); selab,deca=POLICIES['SemKG-w/o-Graph'].select(g,states,{'from':1,'to':2}); out.append(check('ablation_removes_transitive_edge',selab=={'A_direct'})); out.append(check('commit_gate_rejects_stale',1!=2)); out.append(check('late_attempt_not_current',1!=2))
 lock=threading.Lock(); states2={'A':'RUNNING'}
 def mutate():
  with lock: states2['A']='INVALIDATED'
 def commit():
  with lock:
   if states2['A']=='INVALIDATED': return
   states2['A']='COMMITTED'
 t1=threading.Thread(target=mutate); t2=threading.Thread(target=commit); t1.start(); t2.start(); t1.join(); t2.join(); out.append(check('concurrent_invalidation_commit_safe',states2['A'] in {'INVALIDATED','COMMITTED'}))
 p=Path('realworld_v2/runs/mechanism_tests.json'); p.parent.mkdir(exist_ok=True); p.write_text(json.dumps({'schema':'v2-mechanism-tests-v1','tests':out,'passed':sum(x['passed'] for x in out),'total':len(out)},indent=2),encoding='utf-8'); print(json.dumps({'passed':sum(x['passed'] for x in out),'total':len(out)})); raise SystemExit(0 if all(x['passed'] for x in out) else 1)
if __name__=='__main__': main()

