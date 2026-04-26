from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from detrix.workers.ml_intern import (
    MLInternPrivacyError,
    MLInternWorker,
    MLInternWorkerConfig,
    assert_ml_intern_result_can_enter_governance,
)


def _source_checkout(tmp_path: Path) -> Path:
    source = tmp_path / "ml-intern"
    (source / "configs").mkdir(parents=True)
    (source / "configs" / "cli_agent_config.json").write_text(
        json.dumps({"save_sessions": True, "auto_file_upload": True}),
        encoding="utf-8",
    )
    (source / "pyproject.toml").write_text("[project]\nname='ml-intern'\n", encoding="utf-8")
    (source / ".env").write_text("HF_TOKEN=secret\n", encoding="utf-8")
    (source / ".git").mkdir()
    (source / "package.py").write_text("print('ok')\n", encoding="utf-8")
    return source


def _config(tmp_path: Path, source: Path) -> MLInternWorkerConfig:
    return MLInternWorkerConfig(
        ml_intern_source_dir=source,
        run_root=tmp_path / "runs",
        model_name="Qwen/Qwen3.5-test",
        timeout_seconds=5,
        max_iterations=2,
    )


def test_rewrites_reads_back_privacy_config_and_builds_source_checkout_command(tmp_path: Path) -> None:
    source = _source_checkout(tmp_path)
    calls: list[dict[str, object]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append({"command": command, **kwargs})
        cwd = Path(str(kwargs["cwd"]))
        output = cwd.parent / "outputs" / "adapter"
        output.mkdir(parents=True)
        (output / "adapter_model.safetensors").write_text("adapter", encoding="utf-8")
        (cwd.parent / "outputs" / "training_result.json").write_text("{}", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="done", stderr="")

    worker = MLInternWorker(_config(tmp_path, source), runner=fake_run)
    result = worker.run("synthetic scratch-only Qwen SFT investigation")

    assert result.exit_code == 0
    assert result.redaction_status == "clean"
    assert result.command[:4] == ["uv", "run", "--project", result.cwd]
    assert result.command[4:6] == ["python", f"{result.cwd}/detrix_safe_headless.py"]
    assert "ml-intern" not in result.command
    assert "--max-iterations" in result.command
    assert result.cwd.endswith("ml-intern-src")

    copied_config = json.loads(Path(result.privacy_config_path).read_text(encoding="utf-8"))
    assert copied_config["save_sessions"] is False
    assert copied_config["auto_file_upload"] is False
    assert copied_config["yolo_mode"] is False
    assert copied_config["confirm_cpu_jobs"] is True
    assert copied_config["mcpServers"] == {}
    assert copied_config["model_name"] == "Qwen/Qwen3.5-test"
    assert copied_config["auto_save_interval"] == 0
    assert copied_config["heartbeat_interval_s"] == 0

    copied_root = Path(result.cwd)
    assert not (copied_root / ".env").exists()
    assert not (copied_root / ".git").exists()
    assert str(calls[0]["cwd"]) == result.cwd


def test_missing_source_checkout_fails_closed(tmp_path: Path) -> None:
    config = MLInternWorkerConfig(
        ml_intern_source_dir=tmp_path / "missing",
        run_root=tmp_path / "runs",
        model_name="model",
    )
    worker = MLInternWorker(config)
    with pytest.raises(MLInternPrivacyError):
        worker.run("prompt")


def test_timeout_returns_structured_result(tmp_path: Path) -> None:
    source = _source_checkout(tmp_path)

    def fake_timeout(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(command, timeout=5, output=b"partial", stderr=b"slow")

    worker = MLInternWorker(_config(tmp_path, source), runner=fake_timeout)
    result = worker.run("prompt")

    assert result.timed_out is True
    assert result.exit_code is None
    assert Path(result.stdout_path).read_text(encoding="utf-8") == "partial"
    assert Path(result.stderr_path).read_text(encoding="utf-8") == "slow"


def test_artifact_allowlist_blocks_forbidden_files(tmp_path: Path) -> None:
    source = _source_checkout(tmp_path)

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        cwd = Path(str(kwargs["cwd"]))
        out = cwd.parent / "outputs"
        (out / "reports").mkdir(parents=True)
        (out / "reports" / "summary.json").write_text("{}", encoding="utf-8")
        (out / "hf_token").write_text("secret", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    worker = MLInternWorker(_config(tmp_path, source), runner=fake_run)
    result = worker.run("prompt")

    assert result.redaction_status == "blocked"
    blocked = [a.relative_path for a in result.artifact_manifest if a.redaction_status == "blocked"]
    assert "hf_token" in blocked
    with pytest.raises(MLInternPrivacyError):
        assert_ml_intern_result_can_enter_governance(result)


def test_files_outside_output_directory_block_result(tmp_path: Path) -> None:
    source = _source_checkout(tmp_path)

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        cwd = Path(str(kwargs["cwd"]))
        (cwd / "leaked_dataset.json").write_text("{}", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    worker = MLInternWorker(_config(tmp_path, source), runner=fake_run)
    result = worker.run("prompt")

    assert result.redaction_status == "blocked"
    assert "ml-intern-src/leaked_dataset.json" in [
        artifact.relative_path for artifact in result.artifact_manifest
    ]


def test_modified_source_checkout_file_blocks_result(tmp_path: Path) -> None:
    source = _source_checkout(tmp_path)

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        cwd = Path(str(kwargs["cwd"]))
        (cwd / "package.py").write_text("raw generated data", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    worker = MLInternWorker(_config(tmp_path, source), runner=fake_run)
    result = worker.run("prompt")

    assert result.redaction_status == "blocked"
    assert "ml-intern-src/package.py" in [
        artifact.relative_path for artifact in result.artifact_manifest
    ]


def test_output_symlink_blocks_result(tmp_path: Path) -> None:
    source = _source_checkout(tmp_path)
    target = tmp_path / "outside.safetensors"
    target.write_text("outside run data", encoding="utf-8")

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        cwd = Path(str(kwargs["cwd"]))
        adapter_dir = cwd.parent / "outputs" / "adapter"
        adapter_dir.mkdir(parents=True)
        (adapter_dir / "adapter_model.safetensors").symlink_to(target)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    worker = MLInternWorker(_config(tmp_path, source), runner=fake_run)
    result = worker.run("prompt")

    assert result.redaction_status == "blocked"
    assert "adapter/adapter_model.safetensors" in [
        artifact.relative_path for artifact in result.artifact_manifest
    ]


def test_stdout_symlink_is_replaced_before_metadata_write(tmp_path: Path) -> None:
    source = _source_checkout(tmp_path)
    outside_target = tmp_path / "outside.log"
    outside_target.write_text("do not overwrite", encoding="utf-8")

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        cwd = Path(str(kwargs["cwd"]))
        (cwd.parent / "outputs" / "stdout.log").symlink_to(outside_target)
        return subprocess.CompletedProcess(command, 0, stdout="captured", stderr="")

    worker = MLInternWorker(_config(tmp_path, source), runner=fake_run)
    result = worker.run("prompt")

    stdout_path = Path(result.stdout_path)
    assert stdout_path.read_text(encoding="utf-8") == "captured"
    assert not stdout_path.is_symlink()
    assert outside_target.read_text(encoding="utf-8") == "do not overwrite"
    assert result.redaction_status == "clean"


def test_output_directory_symlink_is_recreated_before_metadata_write(tmp_path: Path) -> None:
    source = _source_checkout(tmp_path)
    outside_dir = tmp_path / "outside-output"
    outside_dir.mkdir()

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        cwd = Path(str(kwargs["cwd"]))
        output_dir = cwd.parent / "outputs"
        shutil.rmtree(output_dir)
        output_dir.symlink_to(outside_dir, target_is_directory=True)
        return subprocess.CompletedProcess(command, 0, stdout="captured", stderr="captured err")

    worker = MLInternWorker(_config(tmp_path, source), runner=fake_run)
    result = worker.run("prompt")

    assert Path(result.stdout_path).read_text(encoding="utf-8") == "captured"
    assert Path(result.stderr_path).read_text(encoding="utf-8") == "captured err"
    assert not Path(result.stdout_path).parent.is_symlink()
    assert not (outside_dir / "stdout.log").exists()
    assert not (outside_dir / "stderr.log").exists()
    assert result.redaction_status == "blocked"
    assert "outputs" in [artifact.relative_path for artifact in result.artifact_manifest]


def test_caller_env_cannot_override_privacy_isolation(tmp_path: Path) -> None:
    source = _source_checkout(tmp_path)
    config = _config(tmp_path, source).model_copy(update={"env": {"HOME": "/tmp/unsafe"}})
    worker = MLInternWorker(config, runner=lambda command, **kwargs: subprocess.CompletedProcess(command, 0))

    with pytest.raises(MLInternPrivacyError, match="HOME"):
        worker.run("prompt")


def test_worker_module_does_not_import_governance_persistence_or_promotion() -> None:
    source = Path("src/detrix/workers/ml_intern.py").read_text(encoding="utf-8")
    assert "TrajectoryStore" not in source
    assert "ModelPromoter" not in source
    assert "GovernanceGate" not in source


def test_result_timestamps_are_captured(tmp_path: Path) -> None:
    source = _source_checkout(tmp_path)
    now = datetime(2026, 4, 26, tzinfo=timezone.utc)
    times = iter([now, now + timedelta(seconds=1), now + timedelta(seconds=2)])

    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    worker = MLInternWorker(_config(tmp_path, source), runner=fake_run, clock=lambda: next(times))
    result = worker.run("prompt")

    assert result.started_at == now + timedelta(seconds=1)
    assert result.finished_at == now + timedelta(seconds=2)
