from __future__ import annotations

from click.testing import CliRunner

from detrix.cli.main import cli


def test_openclaw_demo_runs_end_to_end(tmp_path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "openclaw",
            "demo",
            "tests/fixtures/openclaw_sample.jsonl",
            "--db",
            str(tmp_path / "evidence.db"),
            "--output-dir",
            str(tmp_path / "exports"),
            "--max-paragraph",
            "200",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Detrix OpenClaw Reliability Harness" in result.output
    assert "Replay suite: 6/6 passed" in result.output
    assert "Admission contract portability" in result.output
    assert (tmp_path / "exports" / "routed.sft.jsonl").exists()
    assert (tmp_path / "exports" / "routed.dpo.jsonl").exists()
