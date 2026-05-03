from __future__ import annotations

from detrix.openclaw.trace_digest import digest_openclaw_traces
from detrix.runtime.trajectory_store import TrajectoryStore


def test_openclaw_trace_digest_emits_governed_trajectories(tmp_path) -> None:
    store = TrajectoryStore(str(tmp_path / "evidence.db"))

    summary = digest_openclaw_traces(
        "tests/fixtures/openclaw_sample.jsonl",
        store=store,
        config={"max_paragraph_chars": 200},
    )

    assert summary.total == 3
    assert summary.stored == 3
    assert summary.decisions["accept"] == 1
    assert summary.decisions["caution"] == 2
    assert summary.failure_patterns["paragraph_density_exceeded"] == 1
    assert summary.failure_patterns["apology_as_content"] == 1

    stored = store.query(domain="openclaw", limit=None)
    assert len(stored) == 3
    assert {trajectory.training_route for trajectory in stored} == {"sft", "dpo"}
    assert all(trajectory.replay_status == "pending" for trajectory in stored)


def test_openclaw_trace_digest_skips_malformed_lines(tmp_path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text('{"session_id":"ok","agent_output":"hello"}\nnot-json\n', encoding="utf-8")

    summary = digest_openclaw_traces(path)

    assert summary.total == 1
    assert summary.skipped == 1
