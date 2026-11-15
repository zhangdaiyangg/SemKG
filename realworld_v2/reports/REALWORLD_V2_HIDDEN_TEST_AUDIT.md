# REALWORLD_V2_HIDDEN_TEST_AUDIT

# REALWORLD_V2_HIDDEN_TEST_VALIDATION

The independent five-category validator passes positive v2 artifacts and rejects retained v1 artifacts for all five categories. The API-error case now uses an absent-error input: v2 raises the independently expected `MissingError`, while v1 returns `None`. Price-unit, state-machine, idempotency, and configuration scenarios also have discriminating v1/v2 outputs. Results are in `runs/hidden_test_validation.json`.

The runtime evaluator uses an independent oracle table and does not generate expectations by reading the implementation under test.

Formal rows keep independent evaluator results. The 8 formal failures are retained and are not converted to protocol successes.
