# SemKG anonymous review artifact

Artifact revision: `2026-10-18-review` (strict matched-pair audit, cost decomposition, and frozen graph-edge replay). The distributable review bundle is `artifact/semkg-review-artifact.zip`; the earlier `semkg-selective-r6.zip` remains available for the simulator-only artifact.

Public repository: <https://github.com/zhangdaiyangg/SemKG>

This directory is the reproducibility entry point for the paired discrete-event
simulation, repository audit, graph replay, and executable contract-test sanity
check for the SemKG artifact.

## Reproduce

From the repository root run:

```powershell
powershell -ExecutionPolicy Bypass -File artifact/review_bundle_staging/realworld_v2/analysis/reproduce_review.ps1
```

The review command consumes frozen traces and regenerates the strict pair audit,
edge replay, cost decomposition, figures, and regression tests without model or
network calls. The simulator-only command remains available as
`artifact/reproduce.ps1`.

## Audit files

- `results/raw_results.csv`: one row per scenario, seed, and protocol.
- `results/summary_wide.csv`: protocol means, including
  `commit_time_stale_accepted` and final direct violations.
- `results/paired_differences.csv`: scenario-then-seed bootstrap intervals.
- `results/historical_transitive_audit_s9_seed0.json`: preserved pre-fix trace.
- `results/semkg_perfect_trace_s9_seed0.json`: corrected rerun of the same case.
- `results/semkg_noisy_commit_audit_s2_seed1.json`: noisy-graph trace showing a missed `PriceUnit` read edge and one accepted true-stale read.
- `results/transitive_audit_summary.csv`: final transitive-staleness audit.
- `results/executable/by_category.csv`: direct-category and multi-hop outcomes.
- `results/experiment_manifest.json`: seeds, protocol order, noise, and cost model.
The expected corrected audit has zero final transitive artifacts and zero
commit-time stale acceptances for SemKG-Perfect. SemKG-Noisy can accept a true
stale read when its graph omits that read edge; the audit trace makes the
observed-versus-true distinction explicit. The graph-cost coefficients are
sensitivity parameters, not deployment measurements.
