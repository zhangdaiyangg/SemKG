# REALWORLD_V2_RESEARCH_CLAIMS

- **SemKG decisions use observed graph traversal** — mechanism: contract:C -> A_direct -> B_transitive runtime edges; metric: selected_tasks, graph_edges, decision_trace; evidence: V2_FORMAL_SUMMARY.csv and raw JSON; limitation: 4 recovery SemKG rows contained missed or false observations and selected only A.
- **SemKG preserves unrelated tasks** — mechanism: graph traversal excludes D/E; metric: correctly_preserved and false_invalidations; evidence: V2_FORMAL_SUMMARY.csv; limitation: controlled injected topology.
- **SemKG reduces unnecessary rework versus Global-Invalidate** — mechanism: selected set is two instead of four; metric: mean rework_count; evidence: SemKG mean=1.906; Global mean=4.000; limitation: model failures and compact tasks.
- **SemKG can miss edges** — mechanism: observed read evidence absent; metric: missed_invalidations; evidence: SemKG missed mean=0.031; limitation: Gold used only after execution for audit.

- **Recovery-block costs are complete** — mechanism: evaluator failures persist accumulated usage before returning; metric: 54,649,418 tokens and USD 3.434305356 across 400 rows; evidence: `REALWORLD_V2_RECOVERY_COST_AUDIT.md`; limitation: 15 evaluator failures remain semantic failures, not successful workflows.

No claim of universal production superiority is supported. The recovery evidence supports a conditional mechanism result: graph traversal reduces unnecessary invalidation when the relevant observed edge is present, while incomplete observation produces explicit missed and false invalidations.

