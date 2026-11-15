"""Export an auditable per-run model token and cost ledger from frozen traces.

This script never calls a model.  It separates cached input, uncached input,
and output tokens, recomputes cost with the rates recorded by the runtime, and
checks the recomputation against each run's stored total.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from controller.v2_runtime import RATES

RUNS = ROOT / "runs" / "formal_recovery"
OUT = ROOT / "reports"


def price(usage: dict) -> float:
    return (
        usage["cache_hit_tokens"] * RATES[0][0]
        + usage["input_tokens_uncached"] * RATES[1][0]
        + usage["output_tokens"] * RATES[2][0]
    ) / 1_000_000


def run_row(path: Path) -> dict:
    row = json.loads(path.read_text(encoding="utf-8"))
    totals = defaultdict(int)
    turns = 0
    for event in row.get("events", []):
        if event.get("kind") != "agent_end":
            continue
        for turn in event.get("trace", []):
            turns += 1
            usage = turn.get("usage", {})
            prompt = int(usage.get("prompt_tokens", 0))
            hit = int(usage.get("prompt_cache_hit_tokens", 0))
            miss = int(usage.get("prompt_cache_miss_tokens", prompt - hit))
            output = int(usage.get("completion_tokens", 0))
            if hit + miss != prompt:
                raise ValueError(f"cache partition mismatch in {path.name}")
            totals["input_tokens"] += prompt
            totals["cache_hit_tokens"] += hit
            totals["input_tokens_uncached"] += miss
            totals["output_tokens"] += output
            totals["total_tokens"] += prompt + output
    recomputed = price(totals)
    stored = float(row.get("total_cost_usd", 0.0))
    if abs(recomputed - stored) > 1e-10:
        raise ValueError(f"cost mismatch in {path.name}: {recomputed} != {stored}")
    return {
        "run_id": row.get("run_id", path.stem),
        "repository": row["repository"],
        "scenario": row["scenario"],
        "protocol": row["protocol"],
        "repeat": row["repeat"],
        "model": row.get("model", ""),
        "turns": turns,
        **dict(totals),
        "recomputed_cost_usd": recomputed,
        "stored_cost_usd": stored,
        "cost_abs_error": abs(recomputed - stored),
        "evaluation_complete": int("all_pass" in row.get("evaluation", {})),
        "end_to_end_pass": int(row.get("evaluation", {}).get("all_pass", False)),
    }


def main() -> None:
    rows = [run_row(path) for path in sorted(RUNS.glob("*.json"))]
    if len(rows) != 400:
        raise ValueError(f"expected 400 frozen runs, found {len(rows)}")
    OUT.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    with (OUT / "TOKEN_LEDGER.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    grouped = {}
    for protocol in sorted({row["protocol"] for row in rows}):
        subset = [row for row in rows if row["protocol"] == protocol]
        grouped[protocol] = {
            "runs": len(subset),
            "turns": sum(row["turns"] for row in subset),
            "input_tokens": sum(row["input_tokens"] for row in subset),
            "cache_hit_tokens": sum(row["cache_hit_tokens"] for row in subset),
            "input_tokens_uncached": sum(row["input_tokens_uncached"] for row in subset),
            "output_tokens": sum(row["output_tokens"] for row in subset),
            "total_tokens": sum(row["total_tokens"] for row in subset),
            "stored_cost_usd": sum(row["stored_cost_usd"] for row in subset),
            "recomputed_cost_usd": sum(row["recomputed_cost_usd"] for row in subset),
            "pass_count": sum(row["end_to_end_pass"] for row in subset),
        }
    report = {
        "schema": "semkg-token-ledger-v1",
        "source": "realworld_v2/runs/formal_recovery/*.json",
        "run_count": len(rows),
        "rates_usd_per_million_tokens": {
            "cache_hit_input": RATES[0][0],
            "uncached_input": RATES[1][0],
            "output": RATES[2][0],
        },
        "partition_rule": "prompt_tokens = prompt_cache_hit_tokens + prompt_cache_miss_tokens",
        "cost_rule": "(cache_hit*0.003 + uncached_input*0.15 + output*0.60) / 1e6",
        "protocol_totals": grouped,
        "all_runs": {
            "input_tokens": sum(row["input_tokens"] for row in rows),
            "cache_hit_tokens": sum(row["cache_hit_tokens"] for row in rows),
            "input_tokens_uncached": sum(row["input_tokens_uncached"] for row in rows),
            "output_tokens": sum(row["output_tokens"] for row in rows),
            "total_tokens": sum(row["total_tokens"] for row in rows),
            "stored_cost_usd": sum(row["stored_cost_usd"] for row in rows),
            "recomputed_cost_usd": sum(row["recomputed_cost_usd"] for row in rows),
        },
    }
    (OUT / "TOKEN_LEDGER.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
