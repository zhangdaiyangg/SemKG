"""Counterfactual edge interventions on frozen pre-decision graphs.

Only the observed graph is changed. Mutation, states, and saved model trace are
fixed. Replays test selection causality, not counterfactual code correctness.
"""
from __future__ import annotations

from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "controller"))
from v2_runtime import ObservedGraph, POLICIES, TaskState


def select(row, edges):
    graph = ObservedGraph()
    graph.edges = copy.deepcopy(edges)
    states = {k: TaskState(**v) for k, v in row["tasks"].items()}
    selected, _ = POLICIES["SemKG-Observed"].select(graph, states, copy.deepcopy(row["mutation"]))
    return sorted(selected)


def replay_row(row):
    edges = row["observed_graph"]["edges"]
    base = select(row, edges)
    assert base == sorted(row["selected_tasks"]), "Saved graph does not reproduce recorded selection"
    interventions = []
    # A logical relation may have several evidence records. Remove all evidence
    # for that src--relation--dst relation, so duplicate paths do not hide it.
    relations = sorted({(e["src"], e["relation"], e["dst"]) for e in edges})
    for src, relation, dst in relations:
        changed = [e for e in edges if (e["src"], e["relation"], e["dst"]) != (src, relation, dst)]
        after = select(row, changed)
        assert set(after) <= set(base), "Deleting edges cannot create reachability"
        interventions.append({"intervention": "remove_relation", "edge": [src, relation, dst],
                              "removed_evidence_records": len(edges) - len(changed),
                              "before": base, "after": after,
                              "lost": sorted(set(base) - set(after)),
                              "has_alternative_path_to_target": dst in after})
    empty = select(row, [])
    assert empty == []
    false_edge = {"src": "contract:C", "relation": "reads", "dst": "D_unrelated",
                  "source": "counterfactual_intervention", "detail": "false edge, not model evidence"}
    added = select(row, edges + [false_edge])
    assert added == sorted(set(base) | {"D_unrelated"})
    return {"original": base, "edge_removals": interventions,
            "no_edges": empty, "false_edge_added": added}


def main():
    records, hashes = [], {}
    elapsed = []
    for path in sorted((ROOT / "runs/formal_recovery").glob("*.json")):
        raw = path.read_bytes()
        row = json.loads(raw)
        if row["protocol"] != "SemKG-Observed":
            continue
        started = time.perf_counter()
        replay = replay_row(row)
        elapsed.append(time.perf_counter() - started)
        records.append({"run_id": path.stem, "repository": row["repository"],
                        "scenario": row["scenario"], "repeat": row["repeat"], **replay})
        hashes[path.name] = hashlib.sha256(raw).hexdigest()
    removals = [x for r in records for x in r["edge_removals"]]
    summary = {}
    for edge in sorted({tuple(x["edge"]) for x in removals}):
        subset = [x for x in removals if tuple(x["edge"]) == edge]
        summary[" -> ".join(edge)] = {
            "eligible_graphs": len(subset), "selection_changed": sum(bool(x["lost"]) for x in subset),
            "lost_sets": dict(Counter("+".join(x["lost"]) or "none" for x in subset)),
            "alternative_path_remains": sum(x["has_alternative_path_to_target"] for x in subset)}
    report = {"schema": "semkg-frozen-edge-replay-v1", "graphs": len(records),
              "baseline_exact_matches": len(records), "relation_deletions": len(removals),
              "no_edge_empty_sets": sum(not r["no_edges"] for r in records),
              "false_edge_selects_D": sum("D_unrelated" in r["false_edge_added"] for r in records),
              "timing_seconds": {"total": sum(elapsed), "min": min(elapsed),
                                 "mean": sum(elapsed) / len(elapsed), "max": max(elapsed)},
              "removal_summary": summary, "records": records, "input_sha256": hashes,
              "scope": "Offline decision-set causality only; no new model calls or counterfactual hidden-test outcomes."}
    (ROOT / "reports/GRAPH_EDGE_REPLAY.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in {"records", "input_sha256"}}, indent=2))


if __name__ == "__main__":
    main()
