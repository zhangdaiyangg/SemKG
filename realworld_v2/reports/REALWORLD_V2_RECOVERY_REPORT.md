# REALWORLD_V2_RECOVERY_REPORT

Recovery block: 400 fixed manifest keys, 385 complete semantic evaluations, and 15 retained evaluator failures. Every row contains an event trace and a model usage/cost ledger. This block uses the corrected evaluator-error persistence path and is analyzed independently from the earlier V2 ledger.

| Protocol | Complete | Failed | Hidden pass | Mean rework | Mean preserved D/E | Mean false invalidation | Mean missed invalidation | Tokens | Cost (USD) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| StaticDAG | 95 | 5 | 0 | 0.000 | 2.000 | 0.000 | 2.000 | 8580089 | 0.552417 |
| Version-Check | 100 | 0 | 16 | 1.310 | 1.990 | 0.010 | 0.700 | 12455144 | 0.770495 |
| Global-Invalidate | 93 | 7 | 68 | 4.000 | 0.000 | 2.000 | 0.000 | 18471349 | 1.175114 |
| SemKG-Observed | 97 | 3 | 70 | 1.979 | 1.990 | 0.010 | 0.031 | 15142836 | 0.936280 |

All 400 runs: 54649418 tokens, $3.434305356. 15 evaluator-failure rows remain in the denominator and are not treated as semantic passes.

The recovery block passes mechanism, evaluator, selectivity, concurrency, observation, statistics, cost, and reproducibility gates. It supports a conditional claim: observed graph traversal can preserve unrelated tasks when runtime edges are present, while observation failures and Agent artifact failures remain measurable.
