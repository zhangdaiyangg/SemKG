"""Regression checks for matched-repeat statistics and edge interventions."""
from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))
from review_revision_analysis import match, estimate, load_records
from graph_edge_replay import replay_row


def test_disjoint_completion_is_not_a_complete_pair():
    df = pd.DataFrame([
        {"repository": "r", "scenario": "s", "repeat": rep, "protocol": policy,
         "complete": (rep == 0) == (policy == "Global-Invalidate")}
        for rep in [0, 1] for policy in ["Global-Invalidate", "SemKG-Observed"]])
    assert not match(df).both_complete.any()


def test_unmatched_keys_rejected():
    df = pd.DataFrame([
        {"repository": "r", "scenario": "s", "repeat": i, "protocol": p, "complete": True}
        for i, p in enumerate(["Global-Invalidate", "SemKG-Observed"])])
    with pytest.raises(AssertionError):
        match(df)


def test_frozen_counts_and_no_missing_resources():
    df, hashes = load_records()
    pairs = match(df)
    assert len(hashes) == 400
    assert len(pairs) == 100 and pairs.both_complete.sum() == 90
    assert df.groupby("protocol").success.sum().to_dict() == {
        "Global-Invalidate": 68, "SemKG-Observed": 70, "StaticDAG": 0, "Version-Check": 16}


def test_seeded_cluster_estimate_and_direction():
    df, _ = load_records()
    pairs = match(df)
    first = estimate(pairs, "success", n=1000)
    assert first == estimate(pairs.sample(frac=1, random_state=42), "success", n=1000)
    assert first["cell_weighted_difference"] == pytest.approx(.02)


def fixture_graph(extra_direct=False):
    edges = [{"src": "contract:C", "relation": "reads", "dst": "A_direct"},
             {"src": "A_direct", "relation": "artifact_to_task", "dst": "B_transitive"}]
    if extra_direct:
        edges.append({"src": "contract:C", "relation": "reads", "dst": "B_transitive"})
    return {"observed_graph": {"edges": edges}, "tasks": {}, "mutation": {"from": 1, "to": 2},
            "selected_tasks": ["A_direct", "B_transitive"]}


def test_remove_unique_transitive_path():
    result = replay_row(fixture_graph())
    deletion = next(x for x in result["edge_removals"] if x["edge"][0] == "A_direct")
    assert deletion["after"] == ["A_direct"]
    assert result["no_edges"] == []


def test_alternative_path_preserves_consumer():
    result = replay_row(fixture_graph(True))
    deletion = next(x for x in result["edge_removals"] if x["edge"][0] == "A_direct")
    assert deletion["after"] == ["A_direct", "B_transitive"]
    assert deletion["has_alternative_path_to_target"]
