# Paper-to-code alignment (PDF baseline)

This audit treats the supplied SemKG PDF as the normative experimental
description. It compares that description with
`realworld_v2/runs/formal_recovery/*.json` and the frozen controller.

## Matches

- Five pinned repositories: Click, Flask, pytest, Requests, and Rich.
- Four formal mutations: `price_unit`, `api_error`, `state_machine`, and
  `idempotency`; five repetitions per repository and four protocols produce
  400 workflows.
- Four tasks per workflow, with `A_direct` and `B_transitive` affected and
  `D_unrelated` and `E_unrelated` unrelated.
- Protocols: StaticDAG, Version-Check, Global-Invalidate, and
  SemKG-Observed.
- Frozen traces total 54,649,418 model tokens and `$3.434305356`; the token
  ledger recomputes the same cost from separate cached-input, uncached-input,
  and output fields.
- The PDF's 518 contract-read and 285 artifact-read counts are distinct
  first-attempt `(run_id, task_id, path)` records. Raw event counts are higher
  because rework attempts repeat reads; this distinction is now documented in
  the manifest and ledger.
- The graph replay reproduces all 100 SemKG decision sets. The current replay
  reports its own timing; it is an offline decision-path measurement, not a
  deployed graph-service latency measurement.

## Remaining availability limitation

The five underlying repositories are available at the public URLs and pinned
by commit SHA in `REPRODUCTION_MANIFEST.json`. The SemKG controller and frozen
traces are packaged locally in `semkg-review-artifact.zip`, including source
snapshots, prompts, mutation definitions, replay scripts, token ledgers, and
SHA-256 checksums. However, no public or anonymous URL for the SemKG artifact
package has been published yet. Therefore the package is complete for a
separate artifact upload, but the requirement for a reviewer-clickable public
code repository is not yet satisfied.
