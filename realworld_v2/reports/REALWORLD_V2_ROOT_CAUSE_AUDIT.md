# REALWORLD_V2_ROOT_CAUSE_AUDIT

Date: 2026-10-18

## Frozen evidence

The previous paper, old `realworld/` implementation, 72-run Pilot, 400-run formal traces, graph measurements, and reports are preserved unchanged. V2 uses `realworld_v2/`; hash records are in `manifests/OLD_ARTIFACT_HASHES.json`.

## Root causes

1. **M1: no graph decision path.** `realworld/controller/workflow_runner.py` never imports `observed_graph.py`. The condition `protocol in {"Version-Check", "Global-Invalidate", "SemKG-Observed"}` unconditionally assigns one rework after mutation. Removing graph construction would not alter the formal rows.
2. **M2: evaluator temporal leakage.** The hidden subprocess runs after mutation and imports the final consumer. Several agents delegate to the mutated contract at runtime, so the test evaluates post-mutation behavior rather than the committed attempt's old assumption. The API-error test uses an input for which v1 and v2 agree.
3. **M3: no selection topology.** The old harness creates one consumer and no unaffected concurrent tasks. Global-Invalidate, Version-Check, and SemKG-Observed therefore have the same rework cardinality by construction.
4. **Gold/observed separation was incomplete.** `observed_graph.py` produced independent AST files for measurement, but its output was not consumed by the workflow runner. The formal outcome was therefore neither graph-driven nor traceable as `Contract Event -> Observed Edges -> Traversal -> Selected Tasks`.
5. **Cost incompleteness.** Prior graph measurements were a standalone AST microbenchmark rather than the graph decision path used by a scheduler; workflow rows lacked graph traversal and commit-gate timing.
6. **Concurrency evidence was insufficient.** The old runner invoked one agent at a time. It did not record overlapping task intervals or guarantee mutation after a stale contract read.

## V2 acceptance consequences

V2 must use a policy interface and graph query in the SemKG path, preserve task attempts with assumption versions, commit only current attempts, include two affected and two unaffected tasks, record monotonic event intervals, and validate v1 artifacts against an independently authored v2 oracle. The old data cannot be merged into V2 statistics.
