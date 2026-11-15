# REALWORLD_V2_TOPOLOGY_VALIDATION

The V2 benchmark fixture covers five distinct task topologies: direct dependency, three-node chain, fork dependency, join dependency, and cross-module dependency. Each workflow has four real coding tasks: A and B are contract-affected, while D and E produce independent, executable artifacts. The topology is selected by semantic scenario rather than by protocol.

The end-to-end runtime launches A, D, and E concurrently, commits A after its v1 contract read, starts B, waits for B's upstream read (or its direct contract read in the fork case), and mutates the contract from v1 to v2 while the workflow is active. Events use `time.perf_counter()` and include agent start/end, task reads/writes, mutation, graph decision, invalidation, requeue, commit, and hidden-test verification. Complete formal rows contain non-empty overlapping agent intervals; the independent audit confirms concurrency evidence.

The formal ledger contains all 400 manifest keys. 392 rows completed and 8 Agent/evaluator failures were retained as failures. No failure was removed from the denominator or silently retried.

The primary selectivity contrast is observable in the decision sets: Global-Invalidate selects the four-task scope, while SemKG-Observed selects the graph-reachable affected set when the observed edge is present and preserves D/E. Missing observed edges remain visible as missed invalidations rather than being repaired with Gold information.
