# REALWORLD_V2_PILOT_REPORT

The V2 Pilot manifest contains 72 paired workflows: 3 pinned repositories × 2 semantic scenarios × 4 protocols × 3 repeats. 68 completed JSON traces and 4 retained failure records are present.

| Protocol | Rows | Hidden pass | Rework task count | Stale/invalid observations |
|---|---:|---:|---:|---:|
| StaticDAG | 18 | 0 | 0 | 18 |
| Version-Check | 18 | 1 | 18 | 0 |
| Global-Invalidate | 18 | 15 | 60 | 0 |
| SemKG-Observed | 18 | 15 | 35 | 0 |

All successful SemKG-Observed rows record graph edges and select A_direct plus B_transitive while preserving D_unrelated and E_unrelated. Failures are retained as model/evaluator outcomes; no row was silently retried. The Pilot is used to freeze the mechanism implementation and identify ordinary Agent failure modes before formal execution.
