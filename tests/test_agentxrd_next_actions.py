import json

from detrix.agentxrd.next_actions import build_governed_next_actions


def test_next_actions_are_bounded_and_keep_training_blocked(tmp_path):
    patterns = tmp_path / "failure_patterns.jsonl"
    patterns.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "sample_id": "row-truth",
                        "high_level_bucket": "TRUTH_CONFLICT",
                        "low_level_bucket": "truth_flags",
                        "blocker_class": "TRUTH_CONFLICT",
                        "deterministic_export_label": "eval_only",
                        "source_artifacts": ["artifact.json"],
                    }
                ),
                json.dumps(
                    {
                        "sample_id": "row-prov",
                        "high_level_bucket": "PROVENANCE_GAP",
                        "low_level_bucket": "candidate_cif_provenance",
                        "blocker_class": "PROVENANCE_GAP",
                        "deterministic_export_label": "eval_only",
                        "source_artifacts": ["artifact.json"],
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    actions = build_governed_next_actions(
        patterns, tmp_path / "governed_next_actions.jsonl"
    )

    assert [action.action_type for action in actions] == ["truth_audit", "provenance_join"]
    assert all(action.training_export_blocked for action in actions)
    assert all(action.allowed_commands for action in actions)
    assert all(action.kill_criteria for action in actions)
