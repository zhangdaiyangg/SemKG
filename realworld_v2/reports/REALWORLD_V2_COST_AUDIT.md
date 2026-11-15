# REALWORLD_V2_COST_AUDIT

The cost audit recomputes model usage from stored Agent turn records for every complete run. There are 392 complete formal traces and 8 retained failure records. Complete traces account for 53,185,311 recorded model tokens and USD 3.351950658 under the frozen DeepSeek pricing rule. The eight failure records do not contain a returned usage ledger because the runtime exception occurred before `run_workflow` returned; their cost is therefore unknown, not zero.

This is an explicit failed cost-validity gate. The total above must not be described as the complete system cost for all 400 workflows. The failure run IDs and exception text are in `V2_INDEPENDENT_AUDIT.json`.

Graph coordination timing is measured by replaying the same `ObservedGraph` implementation over the complete decision traces. Across 392 complete rows:

| Mode | Total seconds |
|---|---:|
| Cold graph rebuild | 0.0018759007 |
| Warm graph rebuild | 0.0014070 |
| Incremental graph update | 0.0013553 |

These figures measure the V2 decision-path graph operations, not the old standalone AST microbenchmark. Agent execution, rework, hidden-test time, makespan, and model cost remain separate fields in `V2_FORMAL_SUMMARY.csv`.

Because eight failures lack usage records, current evidence supports cost comparisons only on complete traces and does not support an all-400 cost claim. The runtime should persist usage in a `finally` path before a future formal data freeze; changing that instrumentation would require a new, separately frozen evaluation block rather than silently patching these results.

This audit applies only to the earlier formal ledger. It is superseded for final reporting by `REALWORLD_V2_RECOVERY_COST_AUDIT.md`, where the corrected runtime persisted usage for all 400 recovery runs and the cost gate passes.
