from __future__ import annotations

import json
import re

from click.testing import CliRunner

from detrix.adapters.axv2 import run_artifact_to_trajectories
from detrix.cli.main import cli
from detrix.demo.support_triage import build_demo_artifact
from detrix.improvement.exporter import TrainingExporter
from detrix.runtime.trajectory_store import TrajectoryStore


def test_support_triage_demo_artifact_has_all_terminal_routes() -> None:
    artifact = build_demo_artifact()

    routes = {
        sample_id: route["verdict"]
        for sample_id, route in artifact["terminal_routes"].items()
    }

    assert routes == {
        "accept": "ACCEPT",
        "reject_pii": "REJECT",
        "caution_low_confidence": "CAUTION",
        "request_more_data": "REQUEST_MORE_DATA",
    }
    assert len(artifact["gate_history"]) == 12


def test_demo_adapter_preserves_prompts_and_rejection_types() -> None:
    artifact = build_demo_artifact()
    trajectories = run_artifact_to_trajectories(artifact, domain="support_triage")

    by_sample = {
        trajectory.trajectory_id.rsplit("-", maxsplit=1)[-1]: trajectory
        for trajectory in trajectories
    }

    assert by_sample["accept"].rejection_type is None
    assert by_sample["reject_pii"].rejection_type == "output_quality"
    assert by_sample["caution_low_confidence"].rejection_type == "output_quality"
    assert by_sample["request_more_data"].rejection_type == "input_quality"
    assert by_sample["accept"].prompt == by_sample["reject_pii"].prompt


def test_training_exports_include_accepted_and_dpo_but_block_rejected_sft(tmp_path) -> None:
    artifact = build_demo_artifact()
    store = TrajectoryStore(str(tmp_path / "evidence.db"))
    for trajectory in run_artifact_to_trajectories(artifact, domain="support_triage"):
        store.append(trajectory)

    exporter = TrainingExporter(store)
    sft_path = exporter.export_sft(str(tmp_path / "sft.jsonl"), domain="support_triage")
    dpo_path = exporter.export_dpo(str(tmp_path / "dpo.jsonl"), domain="support_triage")
    grpo_path = exporter.export_grpo(str(tmp_path / "grpo.jsonl"), domain="support_triage")

    sft_rows = [json.loads(line) for line in open(sft_path, encoding="utf-8")]
    dpo_rows = [json.loads(line) for line in open(dpo_path, encoding="utf-8")]
    grpo_rows = [json.loads(line) for line in open(grpo_path, encoding="utf-8")]

    assert len(sft_rows) == 1
    assert len(dpo_rows) == 1
    assert len(grpo_rows) == 1
    rejected = store.get(f"{artifact['run_id']}-reject_pii")
    assert rejected is not None
    try:
        rejected.to_sft_row()
    except ValueError as exc:
        assert "Cannot use rejected trace for SFT" in str(exc)
    else:
        raise AssertionError("Rejected trace unexpectedly converted to SFT")


def test_demo_yc_cli_and_show_run_surface(tmp_path) -> None:
    runner = CliRunner()
    data_dir = tmp_path / ".detrix"
    output_dir = tmp_path / "out"

    result = runner.invoke(
        cli,
        [
            "--data-dir",
            str(data_dir),
            "demo-yc",
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "route=ACCEPT" in result.output
    assert "route=REJECT" in result.output
    assert "route=CAUTION" in result.output
    assert "route=REQUEST_MORE_DATA" in result.output
    assert "SFT export:" in result.output
    assert "DPO export:" in result.output
    assert "blocked" in result.output

    match = re.search(r"Run ID: (yc-demo-[a-f0-9]+)", result.output)
    assert match is not None
    run_id = match.group(1)

    show_result = runner.invoke(
        cli,
        ["--data-dir", str(data_dir), "show-run", run_id],
    )

    assert show_result.exit_code == 0, show_result.output
    assert "Gate verdicts:" in show_result.output
    assert "Terminal routes:" in show_result.output
    assert "pii_detected" in show_result.output
