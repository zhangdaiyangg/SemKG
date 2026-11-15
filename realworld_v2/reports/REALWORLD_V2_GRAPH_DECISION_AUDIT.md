# REALWORLD_V2_GRAPH_DECISION_AUDIT

The first V2 smoke contains a traceable decision chain:

1. A_direct reads `semkg_contract.py` at version 1.
2. B_transitive reads `committed/A_direct/producer.py`, yielding the observed artifact edge.
3. The mutation event increments C from v1 to v2.
4. SemKG-Observed traverses the observed graph and selects A_direct and B_transitive.
5. D_unrelated and E_unrelated are not selected.

The Gold affected set is retained only in the output evaluator for recall accounting. It is not passed to the policy, Agent prompts, graph builder, or commit gate. The graph-off ablation changes the selected set to A_direct, demonstrating that traversal contributes an observable decision difference.
