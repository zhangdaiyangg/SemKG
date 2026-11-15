# REALWORLD_V2_REPRODUCIBILITY_REPORT

Reproduction inputs are the pinned repository manifest, frozen V2 source hashes, Pilot/Formal manifests, raw JSON traces, archived attempt workspaces, independent hidden validator, and aggregation scripts. Formal rows are uniquely keyed and can be re-aggregated without contacting DeepSeek. Non-deterministic Agent text is preserved in event traces; reported metrics are derived from saved outputs.

The formal ledger contains 400 unique keys, 392 complete traces, and 8 retained failure records. `FORMAL_RUN_HASHES.json` hashes every raw formal JSON file; `v2_formal_freeze.json` records the frozen source/model manifest. The independent audit reproduces the gate result and confirms that the prior paper and V1 artifacts retain their recorded SHA-256 hashes.

The final recovery ledger is separately frozen in `v2_recovery_freeze.json`; `FORMAL_RECOVERY_RUN_HASHES.json` hashes all 400 recovery JSON files. The recovery audit re-aggregates 385 complete evaluations and 15 retained evaluator failures without contacting DeepSeek and confirms all eight gates, including complete cost accounting.
