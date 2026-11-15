"""Strict matched-repeat audit of frozen workflows; no model/API calls.

Intervals resample repository--mutation cells with replacement (20 clusters),
preserving matched repeats within each cell. They describe these fixed tasks,
not a non-inferiority test or an estimate for arbitrary repositories.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from realworld_paired_analysis import make_paired_figure, make_combined_figure

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "Global-Invalidate"
TREATMENT = "SemKG-Observed"
KEY = ["repository", "scenario", "repeat"]
METRICS = ["rework", "preserved", "makespan", "cost", "success"]


def load_records():
    records, hashes = [], {}
    for path in sorted((ROOT / "runs/formal_recovery").glob("*.json")):
        data = path.read_bytes()
        row = json.loads(data)
        hashes[path.name] = hashlib.sha256(data).hexdigest()
        ev = row.get("evaluation", {})
        error = row.get("error") or ev.get("error")
        completed = not error and isinstance(ev, dict) and "all_pass" in ev
        selected = set(row["selected_tasks"])
        status = ("complete_pass" if ev.get("all_pass") else "complete_semantic_or_artifact_failure") if completed else (
            "runtime_error_unresolved" if row.get("error") else "artifact_import_or_evaluator_error_unresolved")
        records.append({
            **{k: row[k] for k in KEY}, "protocol": row["protocol"],
            "run_id": path.stem, "complete": bool(completed),
            "success": int(completed and ev.get("all_pass", False)),
            "e2e_success": int(completed and ev.get("all_pass", False)),
            "hidden_pass": int(completed and ev.get("all_pass", False)),
            "rework": len(row["rework_tasks"]),
            "preserved": len({"D_unrelated", "E_unrelated"} - selected),
            "selected_count": len(selected),
            "makespan": row["makespan_seconds"], "cost": row["total_cost_usd"],
            "status": status, "error": error,
        })
    df = pd.DataFrame(records)
    assert len(df) == 400 and not df.duplicated(KEY + ["protocol"]).any()
    assert df.groupby("protocol").size().eq(100).all()
    assert np.isfinite(df[METRICS].to_numpy(dtype=float)).all()
    return df, hashes


def match(df):
    left = df[df.protocol == BASELINE].copy()
    right = df[df.protocol == TREATMENT].copy()
    paired = left.merge(right, on=KEY, suffixes=("_global", "_semkg"),
                        validate="one_to_one", how="outer", indicator=True)
    assert paired._merge.eq("both").all(), "Unmatched design key"
    paired["both_complete"] = paired.complete_global & paired.complete_semkg
    return paired.sort_values(KEY).reset_index(drop=True)


def estimate(pairs, metric, seed=20261018, n=20000):
    # Savings are Global minus SemKG; correctness is SemKG minus Global.
    direction = -1 if metric == "success" else 1
    differences = direction * (pairs[f"{metric}_global"] - pairs[f"{metric}_semkg"])
    tmp = pairs[KEY].copy()
    tmp["difference"] = differences
    cells = tmp.groupby(KEY[:2]).difference.mean().to_numpy(dtype=float)
    rng = np.random.default_rng(seed)
    draws = cells[rng.integers(0, len(cells), size=(n, len(cells)))].mean(axis=1)
    return {"pairs": len(pairs), "cells": len(cells),
            "cell_weighted_difference": float(cells.mean()),
            "pooled_pair_difference": float(differences.mean()),
            "ci_low": float(np.quantile(draws, .025)),
            "ci_high": float(np.quantile(draws, .975))}


def main():
    df, hashes = load_records()
    pairs = match(df)
    strict = pairs[pairs.both_complete].copy()
    results = {label: {metric: estimate(part, metric, 20261018 + i)
                       for i, metric in enumerate(METRICS)}
               for label, part in [("all_runs", pairs), ("both_complete", strict)]}
    contingency = pd.crosstab(pairs.success_global, pairs.success_semkg).reindex(
        index=[0, 1], columns=[0, 1], fill_value=0)
    # Bounds for latent pass outcomes on evaluator-error rows only. Main e2e
    # success always counts these as failures; no favorable imputation is used.
    lo = (pairs.success_semkg - (pairs.success_global + (~pairs.complete_global).astype(int))).mean()
    hi = ((pairs.success_semkg + (~pairs.complete_semkg).astype(int)) - pairs.success_global).mean()
    report = {
        "schema": "semkg-strict-pair-audit-v1", "rows": len(df),
        "pair_key": KEY, "design_pairs": len(pairs),
        "both_complete_pairs": len(strict),
        "only_global_complete": int((pairs.complete_global & ~pairs.complete_semkg).sum()),
        "only_semkg_complete": int((~pairs.complete_global & pairs.complete_semkg).sum()),
        "neither_complete": int((~pairs.complete_global & ~pairs.complete_semkg).sum()),
        "bootstrap": "20000 fixed-seed cell-cluster resamples; equal cell weights; repeats kept matched",
        "direction": "Global minus SemKG for resource metrics; SemKG minus Global for success",
        "results": results,
        "correctness_contingency_rows_global_columns_semkg": contingency.to_dict(orient="split"),
        "latent_correctness_error_imputation_bounds_not_ci": [float(lo), float(hi)],
        "failure_handling": "All error rows retained as e2e failures with measured resources. No error is established to be infrastructure-only; artifact/evaluator import attribution remains unresolved.",
        "protocol_totals": df.groupby("protocol").agg(
            runs=("run_id", "count"), complete=("complete", "sum"), passes=("success", "sum"),
            cost=("cost", "sum"), mean_time_all=("makespan", "mean"),
            mean_rework_all=("rework", "mean")).to_dict(orient="index"),
        "status_counts": df.groupby(["protocol", "status"]).size().to_dict(),
        "input_sha256": hashes,
    }
    report["status_counts"] = {" / ".join(k): int(v) for k, v in report["status_counts"].items()}
    out = ROOT / "reports"
    out.mkdir(exist_ok=True)
    (out / "STRICT_PAIR_AUDIT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    pairs.to_csv(out / "STRICT_MATCHED_PAIRS.csv", index=False)
    df[df.error.notna()].to_csv(out / "RETAINED_FAILURE_CLASSIFICATION.csv", index=False)
    # Plot only exactly matched complete repeats, not separately filtered means.
    keys = strict[KEY]
    matched_df = df[df.protocol.isin([BASELINE, TREATMENT])].merge(keys, on=KEY, validate="many_to_one")
    assert len(matched_df) == 2 * len(strict)
    make_paired_figure(matched_df)
    make_combined_figure(df)
    print(json.dumps({k: v for k, v in report.items() if k != "input_sha256"}, indent=2))


if __name__ == "__main__":
    main()
