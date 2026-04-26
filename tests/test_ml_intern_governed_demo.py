from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from detrix.core.trajectory import GovernedTrajectory
from detrix.core.types import Verdict
from detrix.examples.ml_intern_governed_demo import run_governed_ml_intern_demo
from detrix.runtime.trajectory_store import TrajectoryStore
from detrix.workers.ml_intern import MLInternWorker, MLInternWorkerConfig


def _source_checkout(tmp_path: Path) -> Path:
    source = tmp_path / "ml-intern"
    (source / "configs").mkdir(parents=True)
    (source / "configs" / "cli_agent_config.json").write_text("{}", encoding="utf-8")
    (source / "pyproject.toml").write_text("[project]\nname='ml-intern'\n", encoding="utf-8")
    return source


def _seed_store(path: Path) -> None:
    store = TrajectoryStore(str(path))
    store.append(
        GovernedTrajectory(
            trajectory_id="accepted",
            run_id="axv2-demo",
            domain="xrd",
            prompt=json.dumps({"sample": "s1"}),
            completion=json.dumps({"phase": "quartz"}),
            verdicts=[{"decision": "accept", "gate_id": "metrology", "evidence": {}}],
            governance_score=1.0,
            gate_pass_rate=1.0,
            started_at=datetime(2026, 4, 26, tzinfo=timezone.utc),
        )
    )
    store.append(
        GovernedTrajectory(
            trajectory_id="rejected",
            run_id="axv2-demo",
            domain="xrd",
            prompt=json.dumps({"sample": "s2"}),
            completion=json.dumps({"phase": "wrong"}),
            verdicts=[{"decision": "reject", "gate_id": "metrology", "evidence": {}}],
            governance_score=0.0,
            gate_pass_rate=0.0,
            rejection_type="output_quality",
            started_at=datetime(2026, 4, 26, tzinfo=timezone.utc),
        )
    )


def _worker(tmp_path: Path, runner) -> MLInternWorker:
    return MLInternWorker(
        MLInternWorkerConfig(
            ml_intern_source_dir=_source_checkout(tmp_path),
            run_root=tmp_path / "runs",
            model_name="Qwen/Qwen3.5-test",
        ),
        runner=runner,
    )


def test_governed_demo_exports_only_accepted_rows_and_promotes_non_regression(tmp_path: Path) -> None:
    evidence_db = tmp_path / "evidence.db"
    _seed_store(evidence_db)

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        out = Path(str(kwargs["cwd"])).parent / "outputs" / "reports"
        out.mkdir(parents=True)
        (out / "eval.json").write_text("{}", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="trained", stderr="")

    report = run_governed_ml_intern_demo(
        evidence_db=str(evidence_db),
        output_dir=str(tmp_path / "demo"),
        worker=_worker(tmp_path, fake_run),
        worker_prompt="Synthetic scratch-only training fix.",
        incumbent_metrics={"pass_rate": 0.8, "governance_score": 0.8, "domain_eval": 0.7},
        challenger_metrics={"pass_rate": 0.8, "governance_score": 0.9, "domain_eval": 0.75},
    )

    assert report.verdict == Verdict.PROMOTE
    rows = [json.loads(line) for line in Path(report.sft_export_path).read_text().splitlines()]
    assert len(rows) == 1
    assert report.training_rows == 1
    assert Path(str(report.report_path)).exists()


def test_governed_demo_rejects_blocked_worker_artifacts(tmp_path: Path) -> None:
    evidence_db = tmp_path / "evidence.db"
    _seed_store(evidence_db)

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        out = Path(str(kwargs["cwd"])).parent / "outputs"
        (out / ".env").write_text("TOKEN=secret", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    report = run_governed_ml_intern_demo(
        evidence_db=str(evidence_db),
        output_dir=str(tmp_path / "demo"),
        worker=_worker(tmp_path, fake_run),
        worker_prompt="Synthetic scratch-only training fix.",
        incumbent_metrics={"pass_rate": 0.8, "governance_score": 0.8},
        challenger_metrics={"pass_rate": 0.9, "governance_score": 0.9},
    )

    assert report.verdict == Verdict.REJECT
    assert "ml_intern_artifact_blocked" in report.reason_codes


def test_governed_demo_rejects_pass_rate_regression(tmp_path: Path) -> None:
    evidence_db = tmp_path / "evidence.db"
    _seed_store(evidence_db)

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    report = run_governed_ml_intern_demo(
        evidence_db=str(evidence_db),
        output_dir=str(tmp_path / "demo"),
        worker=_worker(tmp_path, fake_run),
        worker_prompt="Synthetic scratch-only training fix.",
        incumbent_metrics={"pass_rate": 0.8, "governance_score": 0.8},
        challenger_metrics={"pass_rate": 0.79, "governance_score": 0.95},
    )

    assert report.verdict == Verdict.REJECT
    assert "pass_rate_regressed" in report.reason_codes
