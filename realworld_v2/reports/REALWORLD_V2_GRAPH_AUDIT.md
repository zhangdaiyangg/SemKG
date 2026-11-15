# REALWORLD_V2_GRAPH_AUDIT

Observed edges come only from runtime file-read events and are stored with source kind and path. Gold affected tasks appear only in post-run audit fields. SemKG uses `ObservedGraph.affected()`; Global-Invalidate and Version-Check do not call this traversal. The graph-off ablation selects direct readers only.

The formal data include both complete two-edge chains and retained missed-edge cases, so observed recall is not silently treated as perfect.
## Final recovery audit

The recovery block uses the same observed-graph decision path with evaluator-error persistence enabled. Its 400 traces remain separate from the earlier ledger; graph replay totals are 0.0019884 s cold, 0.0016010 s warm, and 0.0014765 s incremental. Graph decisions remain runtime-evidence driven, and false or missed observations are counted after execution.
