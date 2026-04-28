from pathlib import Path

from detrix.agentxrd.drift_replay import run_drift_replay

FIXTURE_ROOT = Path("/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics")
BINARY20 = FIXTURE_ROOT / "binary20_governed_judge_cohort_v0"
ROUTER = FIXTURE_ROOT / "pxrd_failure_router_v0"


def test_drift_replay_blocks_unsafe_sft_positive_delta(tmp_path):
    report = run_drift_replay(
        binary20_artifact=BINARY20 / "detrix_run_artifact.json",
        router_summary=ROUTER / "summary.json",
        output_path=tmp_path / "drift_replay_report.json",
        proposed_metrics={"sft_positive_count": 1, "wrong_accept_count": 1},
    )

    assert report.release_blocked is True
    assert "wrong_accept_regression" in report.block_reasons
    assert report.before["sft_positive_count"] == 0
    assert report.after["sft_positive_count"] == 1
