# REALWORLD_V2_RUNTIME_IMPLEMENTATION

V2 implements a shared `CoordinationPolicy` interface in `controller/v2_runtime.py`. StaticDAG, Version-Check, Global-Invalidate, SemKG-w/o-Graph, and SemKG-Observed share the same DeepSeek Agent runtime, tools, event log, attempt workspace, commit copier, hidden evaluator, and cost model.

SemKG-Observed calls `ObservedGraph.from_events()` and `ObservedGraph.affected()` after mutation. It does not read the Gold affected set or hidden tests. Graph edges are sourced from runtime contract reads and upstream artifact reads. The graph decision is serialized in each run under `decision_trace`, with the selected set, traversal, and edge evidence.

Each task records state, attempt id, assumption version, observed reads, invalidation reason, start/end monotonic times, and committed artifact hashes. Late attempts are not committed after invalidation; selected tasks are requeued with version 2. Global-Invalidate selects the declared task scope, Version-Check selects only observed direct contract readers, and the graph-off ablation selects direct readers without traversal.

The previous hard-coded branch is preserved only as frozen evidence under `realworld_v2/artifacts/workflow_runner_v1_frozen.py`; it is not imported by V2.
