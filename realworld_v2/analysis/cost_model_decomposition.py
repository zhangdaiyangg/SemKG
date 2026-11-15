"""Decompose cost ordering from frozen simulator and agent ledgers."""
from collections import defaultdict
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def main():
    raw = pd.read_csv(ROOT / "semkg_agents/results/raw_results.csv")
    means = raw.groupby("protocol").mean(numeric_only=True)
    a, b = means.loc["Global-Invalidate"], means.loc["SemKG-Perfect"]
    overhead_ticks = b.graph_build_ticks + b.graph_query_ticks + b.coordination_ticks
    overhead_cost = 150*b.graph_build_ticks + 80*b.graph_query_ticks + 100*b.coordination_ticks
    scenarios = json.loads((ROOT / "semkg_agents/results/scenario_manifest.json").read_text())
    ratios = [s["affected_count"] / s["task_count"] for s in scenarios]
    totals = defaultdict(lambda: defaultdict(float))
    for p in sorted((ROOT / "realworld_v2/runs/formal_recovery").glob("*.json")):
        r = json.loads(p.read_text())
        t = totals[r["protocol"]]
        t["runs"] += 1
        t["total_model_cost"] += r["total_cost_usd"]
        for event in r["events"]:
            if event["kind"] != "agent_end":
                continue
            phase = "first_attempt_cost" if event["attempt_id"].endswith("_1") else "rework_cost"
            cost = sum(call["cost_usd"] for call in event.get("trace", []))
            t[phase] += cost
            if phase == "rework_cost" and event["task_id"] in {"D_unrelated", "E_unrelated"}:
                t["unrelated_rework_cost"] += cost
    for t in totals.values():
        assert abs(t["first_attempt_cost"] + t["rework_cost"] - t["total_model_cost"]) < 1e-10
    out = {
        "simulator": {"graph_overhead_ticks": float(overhead_ticks),
                      "semkg_core_makespan": float(b.makespan-overhead_ticks),
                      "global_core_makespan": float(a.makespan),
                      "task_token_saving": float(a.tokens-b.tokens),
                      "graph_token_equivalent_overhead": float(overhead_cost),
                      "net_cost_increase": float(b.total_cost-a.total_cost),
                      "fixed_trace_cost_break_even_scale": float((a.tokens-b.tokens)/overhead_cost),
                      "affected_fraction_min_mean_max": [min(ratios), sum(ratios)/len(ratios), max(ratios)]},
        "repository_model_ledger_all_runs": dict(totals),
        "interpretation": "Proxy graph ticks and token-equivalent weights are not calibrated wall time or USD. Runtime recovery is sequential; Global reruns D/E as well as A/B. Cost decomposition is descriptive, not a controlled scheduling counterfactual."}
    (ROOT / "realworld_v2/reports/COST_MODEL_DECOMPOSITION.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
