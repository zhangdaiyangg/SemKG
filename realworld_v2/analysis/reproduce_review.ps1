$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $Root

# All commands consume frozen traces and simulator ledgers; no model/API calls.
python realworld_v2/analysis/review_revision_analysis.py
python realworld_v2/analysis/graph_edge_replay.py
python realworld_v2/analysis/cost_model_decomposition.py
python realworld_v2/analysis/export_repro_manifest.py
python realworld_v2/analysis/token_ledger.py
python -m pytest realworld_v2/tests/test_review_revision.py -q

Write-Host "Review audit complete. See realworld_v2/reports/STRICT_PAIR_AUDIT.json, GRAPH_EDGE_REPLAY.json, and COST_MODEL_DECOMPOSITION.json."
