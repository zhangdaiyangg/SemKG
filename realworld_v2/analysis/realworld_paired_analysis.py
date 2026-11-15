"""Publication plotting helpers and compatibility entry point.

The unit of inference is the repository x mutation scenario cell (20 cells),
with repeats matched by key. The CLI delegates to review_revision_analysis;
the old independently filtered cell estimator is no longer used.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs" / "formal_recovery"
FIGURES = ROOT.parent / "semkg_agents" / "figures"
REPORTS = ROOT / "reports"
PROTOCOLS = ["StaticDAG", "Version-Check", "Global-Invalidate", "SemKG-Observed"]
COLORS = {
    "StaticDAG": "#7f8c8d",
    "Version-Check": "#3b82a8",
    "Global-Invalidate": "#d66b4f",
    "SemKG-Observed": "#2f8f83",
}


def complete(row: dict) -> bool:
    ev = row.get("evaluation")
    return not row.get("error") and isinstance(ev, dict) and not ev.get("error")


def derived(row: dict) -> dict:
    selected = set(row.get("selected_tasks", []))
    true = set(row.get("true_affected_tasks", []))
    ok = complete(row)
    return {
        # Conditional workflow metrics are undefined for retained evaluator
        # failures and are excluded from efficiency means below.
        "rework": len(row.get("rework_tasks", [])) if ok else np.nan,
        "preserved": len({"D_unrelated", "E_unrelated"} - selected) if ok else np.nan,
        "false_invalidations": len(selected - true) if ok else np.nan,
        "missed_invalidations": len(true - selected) if ok else np.nan,
        "selected_count": len(selected),
        "complete": int(ok),
        "e2e_success": int(bool(row.get("evaluation", {}).get("all_pass"))) if ok else 0,
        "hidden_pass": int(bool(row.get("evaluation", {}).get("all_pass"))) if ok else 0,
        "makespan": row.get("makespan_seconds") if ok else np.nan,
        "cost": row.get("total_cost_usd") if ok else np.nan,
    }


def load() -> pd.DataFrame:
    records = []
    for path in sorted(RUNS.glob("*.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        d = derived(row)
        records.append({
            "run_id": row.get("run_id", path.stem),
            "repository": row.get("repository"),
            "scenario": row.get("scenario"),
            "protocol": row.get("protocol"),
            "repeat": row.get("repeat"),
            **d,
        })
    return pd.DataFrame(records)


def bootstrap_difference(df: pd.DataFrame, metric: str, baseline: str, treatment: str,
                         n: int = 20000, seed: int = 20261018) -> dict:
    key = ["repository", "scenario", "repeat"]
    paired = df[df.protocol == baseline][key + [metric]].merge(
        df[df.protocol == treatment][key + [metric]], on=key,
        suffixes=("_a", "_b"), validate="one_to_one").dropna()
    paired["difference"] = paired[metric + "_a"] - paired[metric + "_b"]
    point = paired.groupby(key[:2]).difference.mean().to_numpy()
    rng = np.random.default_rng(seed)
    draws = np.empty(n)
    for i in range(n):
        idx = rng.integers(0, len(point), len(point))
        draws[i] = point[idx].mean()
    return {
        "baseline": baseline,
        "treatment": treatment,
        "metric": metric,
        "cells": len(point),
        "matched_pairs": len(paired),
        "difference_baseline_minus_treatment": float(point.mean()),
        "ci_low": float(np.quantile(draws, 0.025)),
        "ci_high": float(np.quantile(draws, 0.975)),
    }


def make_paired_figure(df: pd.DataFrame) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    cells = sorted(df[["repository", "scenario"]].drop_duplicates().itertuples(index=False, name=None))
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.4), constrained_layout=True)
    specs = [("rework", "Rework tasks", "lower is better"),
             ("preserved", "Unrelated tasks preserved", "higher is better"),
             ("makespan", "Makespan (s)", "lower is better"),
             ("cost", "Model cost (USD)", "lower is better")]
    for ax, (metric, title, subtitle) in zip(axes.flat, specs):
        for cell in cells:
            vals = []
            for protocol in ["Global-Invalidate", "SemKG-Observed"]:
                z = df[(df.repository == cell[0]) & (df.scenario == cell[1]) & (df.protocol == protocol)][metric].dropna()
                vals.append(float(z.mean()) if len(z) else np.nan)
            if not any(np.isnan(vals)):
                ax.plot([0, 1], vals, color="#c7d1d3", linewidth=.7, alpha=.8, zorder=1)
                ax.scatter([0, 1], vals, s=13, color=[COLORS["Global-Invalidate"], COLORS["SemKG-Observed"]], zorder=2)
        ax.set_xticks([0, 1], ["Global", "SemKG"])
        ax.set_title(title, fontsize=9, pad=5)
        ax.text(.02, .96, subtitle, transform=ax.transAxes, fontsize=7, color="#5b6770", va="top")
        ax.grid(axis="y", alpha=.25)
        ax.spines[["top", "right"]].set_visible(False)
    pair_count = int(df.groupby(["repository", "scenario", "repeat"]).ngroups)
    fig.suptitle(f"Matched complete workflows ({pair_count} pairs; 20 cells)", fontsize=11, fontweight="bold")
    fig.savefig(FIGURES / "realworld_paired_effects.png", dpi=240)
    plt.close(fig)


def make_combined_figure(df: pd.DataFrame) -> None:
    fig, (ax, gx) = plt.subplots(1, 2, figsize=(7.2, 3.4), constrained_layout=True)
    x = np.arange(len(PROTOCOLS))
    complete_rate = [df[df.protocol == p].complete.mean() for p in PROTOCOLS]
    e2e_rate = [df[df.protocol == p].e2e_success.mean() for p in PROTOCOLS]
    conditional = [
        df[df.protocol == p].hidden_pass.sum() / max(1, df[df.protocol == p].complete.sum())
        for p in PROTOCOLS
    ]
    width = .24
    ax.bar(x - width, complete_rate, width, label="Complete evaluation", color="#b7c4c7")
    ax.bar(x, e2e_rate, width, label="End-to-end hidden pass", color="#d66b4f")
    ax.bar(x + width, conditional, width, label="Hidden pass | complete", color="#2f8f83")
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Proportion")
    ax.set_xticks(x, [p.replace("-", "\n") for p in PROTOCOLS], fontsize=8)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.grid(axis="y", alpha=.25)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=6.5, ncol=1, loc="upper right")
    ax.set_title("Correctness denominators", fontsize=9, fontweight="bold")

    sem = df[df.protocol == "SemKG-Observed"]
    glob = df[df.protocol == "Global-Invalidate"]
    labels = ["A only", "A+B", "A+B+D/E"]
    sem_counts = [int((sem.selected_count == 1).sum()), int((sem.selected_count == 2).sum()), int((sem.selected_count >= 3).sum())]
    glob_counts = [int((glob.selected_count == 1).sum()), int((glob.selected_count == 2).sum()), int((glob.selected_count >= 3).sum())]
    x2 = np.arange(3)
    width = .36
    gx.bar(x2 - width / 2, glob_counts, width, label="Global", color=COLORS["Global-Invalidate"])
    gx.bar(x2 + width / 2, sem_counts, width, label="SemKG", color=COLORS["SemKG-Observed"])
    gx.set_xticks(x2, labels, fontsize=8)
    gx.set_ylabel("Workflows")
    gx.set_title("Graph-selected set", fontsize=9, fontweight="bold")
    gx.grid(axis="y", alpha=.25)
    gx.spines[["top", "right"]].set_visible(False)
    gx.legend(frameon=False, fontsize=7)
    fig.suptitle("Real-repository evidence: correctness and mechanism", fontsize=10, fontweight="bold")
    fig.savefig(FIGURES / "realworld_success_graph.png", dpi=240)
    plt.close(fig)


def main() -> None:
    from review_revision_analysis import main as strict_main
    strict_main()


if __name__ == "__main__":
    main()
