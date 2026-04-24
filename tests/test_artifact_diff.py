"""Tests for RunArtifact and diff functionality."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from detrix.core.models import RunRecord, StepResult, StepStatus
from detrix.runtime.artifact import RunArtifact
from detrix.runtime.diff import diff_runs


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


def _make_run_record(run_id: str = "test-001", inputs: dict = None) -> RunRecord:
    now = datetime.utcnow()
    return RunRecord(
        run_id=run_id,
        workflow_name="test-wf",
        workflow_version="1.0",
        started_at=now,
        finished_at=now,
        status=StepStatus.SUCCESS,
        inputs=inputs or {"x": 1},
        step_results=[
            StepResult(
                step_id="s1",
                status=StepStatus.SUCCESS,
                started_at=now,
                finished_at=now,
                duration_ms=100.0,
                input_hash="aaa",
                output_hash="bbb",
                output_data={"result": 42},
            ),
        ],
    )


class TestRunArtifact:
    def test_from_run_record(self):
        record = _make_run_record()
        artifact = RunArtifact.from_run_record(record, git_sha="abc123")
        assert artifact.run_id == "test-001"
        assert artifact.workflow_name == "test-wf"
        assert artifact.code_revision == "abc123"
        assert artifact.inputs_hash != ""
        assert artifact.outputs_hash != ""
        assert len(artifact.step_results) == 1

    def test_save_and_load(self, tmp_dir):
        record = _make_run_record()
        artifact = RunArtifact.from_run_record(record, git_sha="abc123")

        path = Path(tmp_dir) / "artifact.json"
        artifact.save(path)
        assert path.exists()

        loaded = RunArtifact.load(path)
        assert loaded.run_id == artifact.run_id
        assert loaded.inputs_hash == artifact.inputs_hash
        assert loaded.outputs_hash == artifact.outputs_hash
        assert len(loaded.step_results) == 1

    def test_env_spec_captured(self):
        record = _make_run_record()
        artifact = RunArtifact.from_run_record(record)
        assert "python_version" in artifact.env_spec
        assert "platform" in artifact.env_spec


class TestDiffRuns:
    def test_identical_runs_no_changes(self):
        record = _make_run_record()
        a = RunArtifact.from_run_record(record, git_sha="abc")
        b = RunArtifact.from_run_record(record, git_sha="abc")
        report = diff_runs(a, b)
        assert not report.has_changes

    def test_different_inputs_detected(self):
        r1 = _make_run_record(run_id="r1", inputs={"x": 1})
        r2 = _make_run_record(run_id="r2", inputs={"x": 2})
        a = RunArtifact.from_run_record(r1)
        b = RunArtifact.from_run_record(r2)
        report = diff_runs(a, b)
        assert report.inputs_changed
        assert report.has_changes

    def test_step_changes_detected(self):
        r1 = _make_run_record(run_id="r1")
        r2 = _make_run_record(run_id="r2")
        # Modify step output hash in r2
        r2.step_results[0].output_hash = "zzz"
        a = RunArtifact.from_run_record(r1)
        b = RunArtifact.from_run_record(r2)
        report = diff_runs(a, b)
        assert len(report.steps_changed) == 1
        assert report.steps_changed[0].step_id == "s1"
        assert report.steps_changed[0].output_changed

    def test_format_text(self):
        r1 = _make_run_record(run_id="r1", inputs={"x": 1})
        r2 = _make_run_record(run_id="r2", inputs={"x": 2})
        a = RunArtifact.from_run_record(r1)
        b = RunArtifact.from_run_record(r2)
        report = diff_runs(a, b)
        text = report.format_text()
        assert "r1" in text
        assert "r2" in text
        assert "CHANGED" in text

    def test_added_step_detected(self):
        now = datetime.utcnow()
        r1 = _make_run_record(run_id="r1")
        r2 = _make_run_record(run_id="r2")
        r2.step_results.append(
            StepResult(
                step_id="s2",
                status=StepStatus.SUCCESS,
                started_at=now,
                finished_at=now,
                duration_ms=50.0,
                input_hash="ccc",
                output_hash="ddd",
            )
        )
        a = RunArtifact.from_run_record(r1)
        b = RunArtifact.from_run_record(r2)
        report = diff_runs(a, b)
        assert "s2" in report.steps_added
