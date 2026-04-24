"""Tests for the detrix workflow engine.

Covers: YAML parsing, DAG ordering, caching, audit logging,
retry semantics, variable resolution, and idempotent step output.
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
import yaml

from detrix.core.cache import StepCache, _stable_hash, hash_file
from detrix.core.models import RunRecord, StepDef, StepResult, StepStatus, WorkflowDef
from detrix.core.pipeline import (
    WorkflowEngine,
    _resolve_inputs,
    _topo_order,
    parse_workflow,
)
from detrix.runtime.audit import AuditLog

# ---------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def sample_workflow_yaml(tmp_dir):
    """Write a minimal workflow YAML and return its path."""
    wf = {
        "name": "test-pipeline",
        "version": "0.1",
        "description": "A test workflow",
        "steps": [
            {
                "id": "step_a",
                "name": "First Step",
                "function": "test_funcs.step_a",
                "inputs": {"x": "$input.x"},
                "outputs": ["doubled"],
            },
            {
                "id": "step_b",
                "name": "Second Step",
                "function": "test_funcs.step_b",
                "depends_on": ["step_a"],
                "inputs": {"val": "$step_a.doubled"},
                "outputs": ["result"],
            },
        ],
    }
    path = os.path.join(tmp_dir, "workflow.yaml")
    with open(path, "w") as f:
        yaml.dump(wf, f)
    return path


@pytest.fixture
def cache(tmp_dir):
    return StepCache(os.path.join(tmp_dir, "cache.db"))


@pytest.fixture
def audit(tmp_dir):
    return AuditLog(os.path.join(tmp_dir, "audit.db"))


@pytest.fixture
def engine(tmp_dir, cache, audit):
    eng = WorkflowEngine(
        cache=cache,
        audit=audit,
        output_dir=os.path.join(tmp_dir, "output"),
        verbose=False,
    )
    eng.register("test_funcs.step_a", lambda x: {"doubled": x * 2})
    eng.register("test_funcs.step_b", lambda val: {"result": val + 10})
    return eng


# ---------------------------------------------------------------
# YAML Parsing
# ---------------------------------------------------------------


class TestYAMLParsing:
    def test_parse_workflow(self, sample_workflow_yaml):
        wf = parse_workflow(sample_workflow_yaml)
        assert wf.name == "test-pipeline"
        assert wf.version == "0.1"
        assert len(wf.steps) == 2
        assert wf.steps[0].id == "step_a"
        assert wf.steps[1].depends_on == ["step_a"]

    def test_parse_example_pipeline(self):
        """Parse the example pipeline YAML."""
        path = Path(__file__).parent.parent / "examples" / "seed_pipeline.yaml"
        if path.exists():
            wf = parse_workflow(str(path))
            assert wf.name == "example-pipeline"
            assert len(wf.steps) == 3

    def test_retry_config(self, tmp_dir):
        wf = {
            "name": "retry-test",
            "steps": [
                {
                    "id": "s1",
                    "function": "noop",
                    "retry": {
                        "max_attempts": 3,
                        "backoff_seconds": 0.5,
                        "backoff_multiplier": 3.0,
                    },
                }
            ],
        }
        path = os.path.join(tmp_dir, "retry.yaml")
        with open(path, "w") as f:
            yaml.dump(wf, f)
        parsed = parse_workflow(path)
        assert parsed.steps[0].retry.max_attempts == 3
        assert parsed.steps[0].retry.backoff_seconds == 0.5
        assert parsed.steps[0].retry.backoff_multiplier == 3.0


# ---------------------------------------------------------------
# DAG Ordering
# ---------------------------------------------------------------


class TestDAGOrdering:
    def test_linear_chain(self):
        steps = [
            StepDef(id="a", name="A", function="f"),
            StepDef(id="b", name="B", function="f", depends_on=["a"]),
            StepDef(id="c", name="C", function="f", depends_on=["b"]),
        ]
        order = _topo_order(steps)
        assert order.index("a") < order.index("b") < order.index("c")

    def test_diamond_dag(self):
        steps = [
            StepDef(id="a", name="A", function="f"),
            StepDef(id="b", name="B", function="f", depends_on=["a"]),
            StepDef(id="c", name="C", function="f", depends_on=["a"]),
            StepDef(id="d", name="D", function="f", depends_on=["b", "c"]),
        ]
        order = _topo_order(steps)
        assert order.index("a") < order.index("b")
        assert order.index("a") < order.index("c")
        assert order.index("b") < order.index("d")
        assert order.index("c") < order.index("d")

    def test_independent_steps(self):
        steps = [
            StepDef(id="x", name="X", function="f"),
            StepDef(id="y", name="Y", function="f"),
        ]
        order = _topo_order(steps)
        assert set(order) == {"x", "y"}


# ---------------------------------------------------------------
# Variable Resolution
# ---------------------------------------------------------------


class TestVarResolution:
    def test_resolve_input_ref(self):
        context = {"input": {"root_dir": "/data"}}
        resolved = _resolve_inputs({"dir": "$input.root_dir"}, context)
        assert resolved["dir"] == "/data"

    def test_resolve_step_ref(self):
        context = {
            "input": {},
            "step1": {"candidates": [1, 2, 3]},
        }
        resolved = _resolve_inputs({"items": "$step1.candidates"}, context)
        assert resolved["items"] == [1, 2, 3]

    def test_literal_passthrough(self):
        resolved = _resolve_inputs({"flag": True, "n": 42}, {"input": {}})
        assert resolved == {"flag": True, "n": 42}

    def test_unresolved_raises(self):
        with pytest.raises(ValueError, match="Unresolved reference"):
            _resolve_inputs({"x": "$missing.key"}, {"input": {}})


# ---------------------------------------------------------------
# Cache
# ---------------------------------------------------------------


class TestStepCache:
    def test_put_and_get(self, cache):
        inputs = {"x": 5}
        output = {"doubled": 10}
        cache.put("step_a", inputs, output)
        got = cache.get("step_a", inputs)
        assert got == output

    def test_miss(self, cache):
        assert cache.get("nope", {"x": 1}) is None

    def test_different_inputs_different_keys(self, cache):
        cache.put("s", {"x": 1}, {"r": 1})
        cache.put("s", {"x": 2}, {"r": 2})
        assert cache.get("s", {"x": 1}) == {"r": 1}
        assert cache.get("s", {"x": 2}) == {"r": 2}

    def test_invalidate_step(self, cache):
        cache.put("s1", {"a": 1}, {"b": 2})
        cache.put("s2", {"a": 1}, {"b": 3})
        removed = cache.invalidate("s1")
        assert removed == 1
        assert cache.get("s1", {"a": 1}) is None
        assert cache.get("s2", {"a": 1}) == {"b": 3}

    def test_invalidate_all(self, cache):
        cache.put("s1", {"a": 1}, {"b": 2})
        cache.put("s2", {"a": 1}, {"b": 3})
        removed = cache.invalidate()
        assert removed == 2

    def test_stable_hash_deterministic(self):
        a = _stable_hash({"z": 1, "a": 2})
        b = _stable_hash({"a": 2, "z": 1})
        assert a == b

    def test_hash_file(self, tmp_dir):
        p = os.path.join(tmp_dir, "test.txt")
        with open(p, "w") as f:
            f.write("hello")
        h = hash_file(p)
        assert len(h) == 64


# ---------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------


class TestAuditLog:
    def test_record_and_retrieve_run(self, audit):
        record = RunRecord(
            run_id="run-001",
            workflow_name="test",
            workflow_version="1.0",
            status=StepStatus.SUCCESS,
        )
        audit.record_run_start(record)
        record.finished_at = datetime.utcnow()
        audit.record_run_end(record)

        got = audit.get_run("run-001")
        assert got is not None
        assert got["workflow_name"] == "test"
        assert got["status"] == "success"

    def test_record_step(self, audit):
        record = RunRecord(
            run_id="run-002",
            workflow_name="test",
            workflow_version="1.0",
        )
        audit.record_run_start(record)

        now = datetime.utcnow()
        step = StepResult(
            step_id="process",
            status=StepStatus.SUCCESS,
            started_at=now,
            finished_at=now,
            duration_ms=123.4,
            input_hash="abc",
            output_hash="def",
        )
        audit.record_step("run-002", step)

        got = audit.get_run("run-002")
        assert len(got["steps"]) == 1
        assert got["steps"][0]["step_id"] == "process"
        assert got["steps"][0]["duration_ms"] == 123.4

    def test_list_runs(self, audit):
        for i in range(3):
            r = RunRecord(
                run_id=f"run-{i}",
                workflow_name="wf",
                workflow_version="1.0",
            )
            audit.record_run_start(r)
        runs = audit.list_runs()
        assert len(runs) == 3

    def test_list_runs_filtered(self, audit):
        names = ["alpha", "beta", "alpha"]
        for i, name in enumerate(names):
            r = RunRecord(
                run_id=f"run-{name}-{i}",
                workflow_name=name,
                workflow_version="1.0",
            )
            audit.record_run_start(r)
        runs = audit.list_runs(workflow_name="alpha")
        assert len(runs) == 2


# ---------------------------------------------------------------
# Engine — Full Execution
# ---------------------------------------------------------------


class TestWorkflowEngine:
    def test_simple_two_step(self, engine, sample_workflow_yaml):
        wf = parse_workflow(sample_workflow_yaml)
        record = engine.run(wf, inputs={"x": 5})

        assert record.status == StepStatus.SUCCESS
        assert len(record.step_results) == 2
        assert record.step_results[0].output_data == {"doubled": 10}
        assert record.step_results[1].output_data == {"result": 20}

    def test_caching_skips_rerun(self, engine, sample_workflow_yaml):
        wf = parse_workflow(sample_workflow_yaml)

        r1 = engine.run(wf, inputs={"x": 5})
        assert all(not s.cached for s in r1.step_results)

        r2 = engine.run(wf, inputs={"x": 5})
        assert all(s.cached or s.status == StepStatus.CACHED for s in r2.step_results)

    def test_different_inputs_not_cached(self, engine, sample_workflow_yaml):
        wf = parse_workflow(sample_workflow_yaml)

        engine.run(wf, inputs={"x": 5})
        r2 = engine.run(wf, inputs={"x": 7})
        assert r2.step_results[0].output_data == {"doubled": 14}

    def test_step_failure_aborts(self, engine, tmp_dir):
        def fail_step(**kwargs):
            raise RuntimeError("boom")

        engine.register("test_funcs.fail", fail_step)

        wf = WorkflowDef(
            name="fail-test",
            version="1.0",
            steps=[
                StepDef(id="s1", name="S1", function="test_funcs.step_a",
                        inputs={"x": "$input.x"}),
                StepDef(id="s2", name="S2", function="test_funcs.fail",
                        depends_on=["s1"], inputs={"val": "$s1.doubled"}),
                StepDef(id="s3", name="S3", function="test_funcs.step_b",
                        depends_on=["s2"], inputs={"val": "$s2.result"}),
            ],
        )
        record = engine.run(wf, inputs={"x": 3})
        assert record.status == StepStatus.FAILED
        assert len(record.step_results) == 2
        assert record.step_results[0].status == StepStatus.SUCCESS
        assert record.step_results[1].status == StepStatus.FAILED

    def test_retry_on_failure(self, tmp_dir):
        call_count = 0

        def flaky_step(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError(f"fail #{call_count}")
            return {"ok": True}

        cache = StepCache(os.path.join(tmp_dir, "c.db"))
        eng = WorkflowEngine(
            cache=cache,
            output_dir=os.path.join(tmp_dir, "out"),
        )
        eng.register("flaky", flaky_step)

        wf = WorkflowDef(
            name="retry-test",
            version="1.0",
            steps=[
                StepDef(
                    id="s1",
                    name="S1",
                    function="flaky",
                    retry={"max_attempts": 3, "backoff_seconds": 0.01},
                ),
            ],
        )
        record = eng.run(wf)
        assert record.status == StepStatus.SUCCESS
        assert record.step_results[0].attempt == 3

    def test_audit_records_created(self, engine, audit, sample_workflow_yaml):
        wf = parse_workflow(sample_workflow_yaml)
        record = engine.run(wf, inputs={"x": 5})

        run = audit.get_run(record.run_id)
        assert run is not None
        assert run["status"] == "success"
        assert len(run["steps"]) == 2

    def test_step_outputs_written_to_disk(self, engine, sample_workflow_yaml, tmp_dir):
        wf = parse_workflow(sample_workflow_yaml)
        record = engine.run(wf, inputs={"x": 5})

        out_dir = Path(engine.output_dir) / record.run_id
        assert (out_dir / "step_a.json").exists()
        assert (out_dir / "step_b.json").exists()

        with open(out_dir / "step_a.json") as f:
            data = json.load(f)
        assert data == {"doubled": 10}

    def test_run_record_duration(self, engine, sample_workflow_yaml):
        wf = parse_workflow(sample_workflow_yaml)
        record = engine.run(wf, inputs={"x": 5})
        assert record.duration_ms > 0
        assert record.finished_at is not None

    def test_no_cache_engine(self, tmp_dir):
        eng = WorkflowEngine(
            output_dir=os.path.join(tmp_dir, "out"),
        )
        eng.register("f", lambda: {"v": 1})

        wf = WorkflowDef(
            name="nocache",
            version="1.0",
            steps=[StepDef(id="s1", name="S1", function="f")],
        )
        record = eng.run(wf)
        assert record.status == StepStatus.SUCCESS


# ---------------------------------------------------------------
# Integration — example pipeline
# ---------------------------------------------------------------


class TestExamplePipeline:
    def test_example_pipeline_runs(self, tmp_dir):
        """Run the example pipeline end-to-end."""
        from detrix.examples.steps import load_data, process_records, summarize

        cache = StepCache(os.path.join(tmp_dir, "cache.db"))
        audit = AuditLog(os.path.join(tmp_dir, "audit.db"))
        eng = WorkflowEngine(
            cache=cache,
            audit=audit,
            output_dir=os.path.join(tmp_dir, "runs"),
        )
        eng.register("detrix.examples.steps.load_data", load_data)
        eng.register("detrix.examples.steps.process_records", process_records)
        eng.register("detrix.examples.steps.summarize", summarize)

        path = Path(__file__).parent.parent / "examples" / "seed_pipeline.yaml"
        wf = parse_workflow(str(path))
        record = eng.run(wf, inputs={})

        assert record.status == StepStatus.SUCCESS
        assert len(record.step_results) == 3

        # Check load output
        load_out = record.step_results[0].output_data
        assert load_out["count"] == 5
        assert len(load_out["records"]) == 5

        # Check summarize output
        summary = record.step_results[2].output_data["summary"]
        assert summary["total_records"] == 5
        assert "label_distribution" in summary
