# REALWORLD_V2_MECHANISM_AUDIT

{
  "gates": {
    "A_mechanism_validity": true,
    "B_evaluator_validity": true,
    "C_selectivity_validity": true,
    "D_concurrency_validity": true,
    "E_observation_validity": true,
    "F_statistical_validity": true,
    "G_cost_validity": false,
    "H_reproducibility": true
  },
  "semkg_complete": 96,
  "global_complete": 98,
  "version_check_complete": 100,
  "semkg_mean_rework": 1.90625,
  "global_mean_rework": 4.0,
  "semkg_mean_preserved": 2.0,
  "global_mean_preserved": 0.0
}

The decision path is mechanically traceable in each complete SemKG row. The four-task topology yields an observed selectivity difference when the transitive read edge is present. Missed-edge rows are retained as negative observation outcomes.

## Recovery block

The corrected recovery runtime persisted evaluator errors with their accumulated usage ledger. Its independent gate audit reports A, B, C, D, E, F, G, and H all true. The final recovery counts are 385 complete evaluations and 15 retained evaluator failures; SemKG-Observed averages 1.979 rework and 1.990 preserved unrelated tasks, while Global-Invalidate averages 4.000 rework and 0 preserved tasks.
