# SemKG

Artifacts for **SemKG: Coordinating Parallel Coding Agents under Evolving Semantic Contracts**.

## Contents

- `paper/`: latest manuscript PDF, LaTeX source, bibliography, and figures.
- `realworld_v2/`: frozen controller, prompts and change definitions, four
  protocols, formal traces, replay scripts, reports, and tests.
- `artifact/semkg-review-artifact.zip`: offline reviewer bundle with pinned
  repository snapshots, raw traces, SHA-256 manifest, prompts, mutations,
  replay scripts, and token ledgers.

## Reproduce the review audit

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File realworld_v2/analysis/reproduce_review.ps1
```

The command uses the frozen traces only. It makes no model or network calls.
It regenerates the strict pair audit, graph-edge replay, cost decomposition,
reproduction manifest, and input/output/cache token ledger, then runs the
regression tests.

The formal repository experiment contains 400 runs: five pinned Python
repositories, four controlled contract mutations, four coordination policies,
and five repetitions. The token ledger separates cached input, uncached input,
and output tokens and recomputes the reported model cost.

The five underlying repositories are pinned by commit SHA and public source
URL in `realworld_v2/reports/REPRODUCTION_MANIFEST.json`. The SemKG artifact
bundle is included for reviewer download; it should also be attached through
the conference artifact system or a public anonymous release.
