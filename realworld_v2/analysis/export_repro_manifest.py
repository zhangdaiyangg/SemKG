"""Export explicit prompts, mutations, repository pins, and run commands."""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORMAL_SCENARIOS = ["price_unit", "api_error", "state_machine", "idempotency"]
DEFINED_BUT_NOT_FORMAL = ["configuration"]
sys.path.insert(0, str(ROOT))
from controller.v2_runtime import RATES, SYSTEM_PROMPT, TOOLS, contract_pair, task_specs


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    repo_manifest = json.loads((ROOT / "manifests" / "repositories.json").read_text(encoding="utf-8"))
    public_sources = {
        "click": "https://github.com/pallets/click.git",
        "flask": "https://github.com/pallets/flask.git",
        "pytest": "https://github.com/pytest-dev/pytest.git",
        "requests": "https://github.com/psf/requests.git",
        "rich": "https://github.com/Textualize/rich.git",
    }
    for repo in repo_manifest:
        repo["public_source"] = public_sources.get(repo["repository"])
    changes = {}
    prompts = {}
    for scenario in FORMAL_SCENARIOS:
        v1, v2, meta = contract_pair(scenario)
        changes[scenario] = {
            "v1_source": v1,
            "v2_source": v2,
            "oracle_metadata": meta,
        }
        prompts[scenario] = [asdict(spec) for spec in task_specs(scenario)]
    manifest = {
        "schema": "semkg-reproduction-manifest-v1",
        "status": "public repository: https://github.com/zhangdaiyangg/SemKG",
        "repositories": repo_manifest,
        "protocols": ["StaticDAG", "Version-Check", "Global-Invalidate", "SemKG-Observed"],
        "formal_scenarios": list(changes),
        "defined_but_not_formal": DEFINED_BUT_NOT_FORMAL,
        "repetitions_per_cell": 5,
        "formal_run_count": 400,
        "change_definitions": changes,
        "system_prompt": SYSTEM_PROMPT,
        "task_prompts": prompts,
        "tool_schema": TOOLS,
        "token_rates_usd_per_million": {
            "cache_hit_input": RATES[0][0],
            "uncached_input": RATES[1][0],
            "output": RATES[2][0],
        },
        "graph_counting_rule": "paper read counts deduplicate first-attempt runtime reads by (run_id, task_id, path); raw event logs retain repeated rework reads",
        "commands": {
            "token_ledger": "python realworld_v2/analysis/token_ledger.py",
            "export_manifest": "python realworld_v2/analysis/export_repro_manifest.py",
            "strict_audit": "python realworld_v2/analysis/review_revision_analysis.py",
            "graph_replay": "python realworld_v2/analysis/graph_edge_replay.py",
            "cost_decomposition": "python realworld_v2/analysis/cost_model_decomposition.py",
            "tests": "python -m pytest realworld_v2/tests/test_review_revision.py -q",
        },
        "source_sha256": {
            "realworld_v2/controller/v2_runtime.py": digest(ROOT / "controller" / "v2_runtime.py"),
            "realworld_v2/analysis/token_ledger.py": digest(ROOT / "analysis" / "token_ledger.py"),
            "realworld_v2/analysis/export_repro_manifest.py": digest(Path(__file__)),
        },
    }
    out = ROOT / "reports" / "REPRODUCTION_MANIFEST.json"
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
