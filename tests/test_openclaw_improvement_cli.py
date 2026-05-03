from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from detrix.cli.main import cli


def test_openclaw_eval_improvement_cli_promotes_clean_challenger(tmp_path: Path) -> None:
    cases = tmp_path / "cases.jsonl"
    baseline = tmp_path / "baseline.jsonl"
    challenger = tmp_path / "challenger.jsonl"
    report = tmp_path / "report.json"
    cases.write_text(
        '{"case_id":"c1","prompt":"Draft: I am sorry. Build passed.",'
        '"expected_contains":["Build passed"],"forbidden_contains":["sorry"]}\n',
        encoding="utf-8",
    )
    baseline.write_text(
        '{"case_id":"c1","output":"I am sorry. Build passed."}\n', encoding="utf-8"
    )
    challenger.write_text('{"case_id":"c1","output":"Build passed."}\n', encoding="utf-8")

    result = CliRunner().invoke(
        cli,
        [
            "openclaw",
            "eval-improvement",
            str(cases),
            "--baseline",
            str(baseline),
            "--challenger",
            str(challenger),
            "--json-output",
            str(report),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Promotion allowed: true" in result.output
    assert '"promotion_allowed": true' in report.read_text(encoding="utf-8")


def test_openclaw_eval_improvement_cli_fails_on_missing_outputs(tmp_path: Path) -> None:
    cases = tmp_path / "cases.jsonl"
    baseline = tmp_path / "baseline.jsonl"
    challenger = tmp_path / "challenger.jsonl"
    cases.write_text(
        '{"case_id":"c1","prompt":"Draft: Build passed.",'
        '"expected_contains":["Build passed"]}\n',
        encoding="utf-8",
    )
    baseline.write_text("", encoding="utf-8")
    challenger.write_text('{"case_id":"c1","output":"Build passed."}\n', encoding="utf-8")

    result = CliRunner().invoke(
        cli,
        [
            "openclaw",
            "eval-improvement",
            str(cases),
            "--baseline",
            str(baseline),
            "--challenger",
            str(challenger),
        ],
    )

    assert result.exit_code != 0
    assert "Generated outputs do not match proof cases" in result.output
