# REALWORLD_V2_GRAPH_OBSERVATION_AUDIT

This audit is based on the frozen formal run ledger and the independent audit script. The coordinator receives only runtime observations: a contract read creates `contract:C -> task`, and a read of a committed upstream artifact creates `upstream task -> downstream task`. The SemKG policy then performs graph traversal from the mutated contract node.

The raw formal traces contain 392 complete decision paths. Every complete `SemKG-Observed` row records `decision_trace.mode=observed_graph_traversal`, `graph_called=true`, and a traversal list. The observed edges are sourced from `runtime_file_read`; no Gold Graph, hidden-test result, or post-hoc true affected set is passed into policy selection. Gold truth is used only after execution to calculate missed and false invalidations.

The important negative evidence is retained. Nine complete SemKG rows selected only `A_direct` instead of the true `A_direct -> B_transitive` closure because the runtime observation did not contain the artifact edge. These rows are counted as missed invalidations. When the artifact edge is observed, SemKG selects A and B while preserving D and E; Global-Invalidate selects all four tasks.

The graph-disabled mechanism test changes the decision path: the ablation selects only directly observed readers and does not claim graph-driven transitive propagation. This rules out the old protocol-name branch as the source of the SemKG decision in the mechanism fixture.

Limitation: the runtime graph is instrumented from file-read and contract-read events. It is an observed graph, not automatic recovery of all latent business semantics. The formal benchmark uses controlled injected contracts in pinned repositories.

## Recovery freeze

The final recovery block contains 400 graph traces, including 15 evaluator failures with persisted usage. Its graph decisions use the same observed evidence path and are independently hashed in `FORMAL_RECOVERY_RUN_HASHES.json`; the failed evaluator rows are retained rather than removed from the graph-quality denominator.
