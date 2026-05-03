from __future__ import annotations

import json

from detrix.openclaw.replay import run_replay_suite


def test_openclaw_replay_suite_passes_frozen_fixture() -> None:
    report = run_replay_suite("tests/fixtures/openclaw_replay_suite.jsonl")

    assert report.total >= 5
    assert report.regressions == 0
    assert report.promotion_allowed is True


def test_openclaw_replay_detects_regression(tmp_path) -> None:
    fixture = tmp_path / "regression.jsonl"
    fixture.write_text(
        json.dumps(
            {
                "case_id": "bad-expectation",
                "message": "x" * 4100,
                "expected_decision": "accept",
                "expected_reason_codes": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report = run_replay_suite(fixture)

    assert report.regressions == 1
    assert report.promotion_allowed is False
