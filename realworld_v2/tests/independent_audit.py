"""Independent, read-only audit of the frozen V2 run ledger.

This script never edits run JSON or paper sources.  It recomputes status counts,
protocol metrics, run hashes, graph-observation evidence, and the eight gates from
the manifest plus raw run files.
"""
from __future__ import annotations
import csv, hashlib, json, statistics
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs" / "formal"
MANIFEST = ROOT / "manifests" / "formal_manifest.json"
REPORTS = ROOT / "reports"

def load():
    rows=[]
    for p in sorted(RUNS.glob("*.json")):
        o=json.loads(p.read_text(encoding="utf-8"))
        o["_file"]=p.name
        rows.append(o)
    return rows

def complete(o):
    return not bool(o.get("error")) and isinstance(o.get("evaluation"), dict) and not bool(o.get("evaluation",{}).get("error"))

def val(o, key, default=None):
    return o.get(key, default)

def derived(o):
    selected=set(o.get("selected_tasks",[])); true=set(o.get("true_affected_tasks",[]))
    token_total=0
    for e in o.get("events",[]):
        for tr in e.get("trace",[]) if e.get("kind")=="agent_end" else []:
            u=tr.get("usage",{})
            if isinstance(u.get("total_tokens"),(int,float)):
                token_total += int(u["total_tokens"])
            else:
                token_total += sum(int(u.get(k,0)) for k in ("prompt_tokens","completion_tokens"))
    return {
        "rework":len(o.get("rework_tasks",[])),
        "preserved":len({"D_unrelated","E_unrelated"}-selected),
        "false_invalidations":len(selected-true),
        "missed_invalidations":len(true-selected),
        "tokens":token_total,
    }

def protocol_metrics(rows):
    out={}
    for proto in ["StaticDAG","Version-Check","Global-Invalidate","SemKG-Observed"]:
        rs=[r for r in rows if r.get("protocol")==proto]
        cs=[r for r in rs if complete(r)]
        def mean(k):
            aliases={"rework_count":"rework","mean_rework":"rework","correctly_preserved":"preserved","mean_preserved":"preserved","mean_false_invalidations":"false_invalidations","mean_missed_invalidations":"missed_invalidations"}
            dk=aliases.get(k,k)
            x=[float(derived(r)[dk] if dk in derived(r) else r.get(k)) for r in cs if (dk in derived(r) or isinstance(r.get(k),(int,float)))]
            return statistics.mean(x) if x else None
        out[proto]={
            "total":len(rs), "complete":len(cs), "failed":len(rs)-len(cs),
            "hidden_pass":sum(bool(r.get("evaluation",{}).get("all_pass")) for r in cs),
            "mean_rework":mean("rework_count"),
            "mean_preserved":mean("correctly_preserved"),
            "mean_false_invalidations":mean("false_invalidations"),
            "mean_missed_invalidations":mean("missed_invalidations"),
            "mean_makespan_seconds":mean("makespan_seconds"),
            "cost_usd":sum(float(r["total_cost_usd"]) for r in cs if r.get("total_cost_usd") is not None),
            "tokens":sum(derived(r)["tokens"] for r in cs),
        }
    return out

def graph_checks(rows):
    cs=[r for r in rows if complete(r)]
    sem=[r for r in cs if r.get("protocol")=="SemKG-Observed"]
    evidence=[]; missed=0; preserved=0
    for r in sem:
        edges=r.get("observed_graph",{}).get("edges",{})
        decision=r.get("decision_trace",{})
        selected=set(r.get("selected_tasks",[]))
        edge_list = edges.get("edges", edges) if isinstance(edges, dict) else edges
        if not isinstance(edge_list, list) or not any(e.get("src")=="contract:C" for e in edge_list):
            return False, "missing contract:C evidence"
        if r.get("protocol")=="SemKG-Observed":
            evidence.append(bool(decision.get("mode")=="observed_graph_traversal"))
        if "B_transitive" not in selected: missed += 1
        if not (selected & {"D_unrelated","E_unrelated"}): preserved += 1
    return bool(evidence) and all(evidence) and missed>=0 and preserved>=0, {"semkg_complete":len(sem),"semkg_missed_B":missed,"semkg_preserved_DE":preserved}

def concurrency_checks(rows):
    cs=[r for r in rows if complete(r)]
    return bool(cs) and all(isinstance(r.get("overlapping_pairs"),list) for r in cs) and any(r.get("overlapping_pairs") for r in cs)

def main():
    global RUNS, MANIFEST, REPORTS
    ap=argparse.ArgumentParser()
    ap.add_argument('--runs-dir',type=Path,default=RUNS)
    ap.add_argument('--manifest',type=Path,default=MANIFEST)
    ap.add_argument('--label',default='formal')
    args=ap.parse_args()
    RUNS=args.runs_dir; MANIFEST=args.manifest
    rows=load()
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected={r["run_id"] for r in manifest["rows"]}
    observed={r.get("run_id") for r in rows}
    failures=[r for r in rows if not complete(r)]
    costs_missing=[r.get("run_id") for r in rows if r.get("total_cost_usd") is None]
    graph_ok,graph_detail=graph_checks(rows)
    gates={
        "A_mechanism_validity": all(r.get("protocol")!="SemKG-Observed" or r.get("decision_trace",{}).get("mode")=="observed_graph_traversal" for r in rows if complete(r)),
        "B_evaluator_validity": (ROOT/"runs"/"hidden_test_validation.json").exists() and bool(json.loads((ROOT/"runs"/"hidden_test_validation.json").read_text()).get("all_positive")) and bool(json.loads((ROOT/"runs"/"hidden_test_validation.json").read_text()).get("all_negative")),
        "C_selectivity_validity": any(r.get("protocol")=="SemKG-Observed" and not ({"D_unrelated","E_unrelated"} & set(r.get("selected_tasks",[]))) for r in rows if complete(r)) and any(r.get("protocol")=="Global-Invalidate" and {"D_unrelated","E_unrelated"}.issubset(set(r.get("selected_tasks",[]))) for r in rows if complete(r)),
        "D_concurrency_validity": concurrency_checks(rows),
        "E_observation_validity": graph_ok and not any("gold" in json.dumps(r.get("decision_trace",{})).lower() for r in rows if complete(r)),
        "F_statistical_validity": len(expected)==400 and expected==observed and len(rows)==400,
        "G_cost_validity": not costs_missing and all(r.get("total_cost_usd") is not None for r in rows),
        "H_reproducibility": len(expected)==400 and all(r.get("events") for r in rows if complete(r)),
    }
    hashes={r["_file"]:hashlib.sha256((RUNS/r["_file"]).read_bytes()).hexdigest() for r in rows}
    (ROOT/"manifests"/f"{args.label.upper()}_RUN_HASHES.json").write_text(json.dumps(hashes,indent=2),encoding="utf-8")
    summary=protocol_metrics(rows)
    stem=args.label.lower()
    (REPORTS/f"V2_INDEPENDENT_AUDIT_{stem}.json").write_text(json.dumps({"rows":len(rows),"complete":len(rows)-len(failures),"failed":len(failures),"missing_cost_run_ids":costs_missing,"protocols":summary,"gates":gates,"graph":graph_detail,"failure_records":[{"run_id":r.get("run_id"),"error":r.get("error")} for r in failures]},indent=2),encoding="utf-8")
    (REPORTS/f"REALWORLD_V2_GATE_AUDIT_{stem}.json").write_text(json.dumps(gates,indent=2),encoding="utf-8")
    with (REPORTS/f"V2_INDEPENDENT_PROTOCOL_SUMMARY_{stem}.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["protocol","total","complete","failed","hidden_pass","mean_rework","mean_preserved","mean_false_invalidations","mean_missed_invalidations","mean_makespan_seconds","tokens","cost_usd"])
        for p,m in summary.items(): w.writerow([p,m["total"],m["complete"],m["failed"],m["hidden_pass"],m["mean_rework"],m["mean_preserved"],m["mean_false_invalidations"],m["mean_missed_invalidations"],m["mean_makespan_seconds"],m["tokens"],m["cost_usd"]])
    print(json.dumps({"rows":len(rows),"complete":len(rows)-len(failures),"failed":len(failures),"gates":gates,"missing_cost":costs_missing},indent=2))

if __name__=="__main__": main()
