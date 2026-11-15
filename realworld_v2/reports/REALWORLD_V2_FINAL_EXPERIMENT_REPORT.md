# REALWORLD_V2_FINAL_EXPERIMENT_REPORT

The final recovery block contains 400 fixed repository/scenario/protocol/repeat keys. It completed 385 semantic evaluations and retained 15 evaluator failures. All 400 rows contain Agent traces, model usage, and cost fields.

| Protocol | Complete | Failed | Hidden pass | Mean rework | Mean preserved D/E | Mean false invalidation | Mean missed invalidation | Mean makespan (s) | Cost (USD) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| StaticDAG | 95 | 5 | 0 | 0.00 | 2.00 | 0.00 | 2.00 | 36.92 | 0.552 |
| Version-Check | 100 | 0 | 16 | 1.31 | 1.99 | 0.01 | 0.70 | 61.34 | 0.770 |
| Global-Invalidate | 93 | 7 | 68 | 4.00 | 0.00 | 2.00 | 0.00 | 91.53 | 1.175 |
| SemKG-Observed | 97 | 3 | 70 | 1.98 | 1.99 | 0.01 | 0.03 | 67.94 | 0.936 |

The full 400-run ledger contains 54,649,418 model tokens and USD 3.434305356. SemKG-Observed selects the observed graph-reachable set and preserves unrelated tasks when the relevant edges are present. The 15 evaluator failures and all observed missed or false relations remain in the denominator and are listed in the recovery audit artifacts.

All eight gates pass for this recovery block. The earlier V2 ledger remains frozen and is not mixed into these statistics.
