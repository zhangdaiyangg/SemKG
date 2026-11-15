$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

python -m src.semkg_sim --out results --scenarios 40 --seeds 5 --agents 3
python -m src.analyze_results --results results --figures figures
python -m src.sensitivity
python -m src.executable_benchmark --out results/executable

Write-Host "Reproduction complete. Inspect results/summary_wide.csv, results/paired_differences.csv, results/transitive_audit_summary.csv, and results/executable/by_category.csv."
