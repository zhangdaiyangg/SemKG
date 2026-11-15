# REALWORLD_V2_END_TO_END_SMOKE_REPORT (verified rerun)

This verification reran one pinned Requests `price_unit` workflow per protocol after the evaluator and runtime fixes. It used four tasks, three concurrent Agent instances in the first wave, and the independent v2 oracle.

| Protocol | Hidden result | Selected | Rework | Cost (USD) |
|---|---:|---|---|---:|
| StaticDAG | False | none | none | 0.005311 |
| Version-Check | False | A_direct | A_direct | 0.007193 |
| Global-Invalidate | True | A_direct, B_transitive, D_unrelated, E_unrelated | A_direct, B_transitive, D_unrelated, E_unrelated | 0.007965 |
| SemKG-Observed | True | A_direct, B_transitive | A_direct, B_transitive | 0.008983 |

SemKG-Observed selected A_direct and B_transitive from runtime graph evidence and preserved D/E. Global-Invalidate selected all four and passed the v2 oracle in this rerun. StaticDAG and Version-Check retained stale downstream behavior in this direct-plus-transitive scenario, as expected from their definitions. The smoke is a mechanism check, not a statistical estimate.
