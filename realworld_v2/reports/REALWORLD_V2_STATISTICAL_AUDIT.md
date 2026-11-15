# REALWORLD_V2_STATISTICAL_AUDIT

The formal manifest has 400 unique repository/scenario/protocol/repeat keys. Eight rows are retained failures; 392 have complete traces. Per-protocol statistics are computed over complete rows and failure counts are reported separately. No failure was resampled or replaced. Primary comparisons report the observed invalidation set, preserved unrelated tasks, missed edges, rework, makespan, tokens, and cost.

The recovery manifest is a separate frozen 400-key block. It has 385 complete semantic evaluations and 15 retained evaluator failures. Every row is present, has a trace and cost ledger, and is included in the denominator. Recovery per-policy counts are in `V2_INDEPENDENT_PROTOCOL_SUMMARY_recovery.csv`; the eight-gate audit passes statistical completeness and reproducibility.

{
  "StaticDAG": {
    "n_complete": 98,
    "n_failed": 2
  },
  "Version-Check": {
    "n_complete": 100,
    "n_failed": 0
  },
  "Global-Invalidate": {
    "n_complete": 98,
    "n_failed": 2
  },
  "SemKG-Observed": {
    "n_complete": 96,
    "n_failed": 4
  }
}
