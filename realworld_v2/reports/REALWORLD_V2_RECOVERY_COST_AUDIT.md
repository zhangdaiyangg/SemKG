# REALWORLD_V2_RECOVERY_COST_AUDIT

The recovery block persisted usage on every one of 400 runs, including 15 evaluator-failure rows. Recomputed totals are **54,649,418 model tokens** and **$3.434305356**. No row has a missing total_cost_usd.

Graph replay totals for the recovery block are in V2_GRAPH_COST_REPLAY_recovery.csv: cold 0.0019883998 s, warm 0.0016010003 s, incremental 0.0014765005 s. These are decision-path graph timings, not the standalone AST benchmark.

The 15 evaluator failures are retained as failures with costs, so the recovery cost gate passes without treating failed workflows as free or successful.
