from __future__ import annotations

import os
from datetime import datetime

from detrix.core.cache import StepCache
from detrix.core.models import RunRecord, StepDef, StepResult, StepStatus, WorkflowDef
from detrix.core.pipeline import WorkflowEngine
from detrix.runtime.langfuse_observer import LangfuseObserver, WorkflowObserver


class RecordingObserver(WorkflowObserver):
    def __init__(self) -> None:
        self.events: list[tuple] = []

    @property
    def enabled(self) -> bool:
        return True

    def on_workflow_start(
        self,
        *,
        run_id: str,
        workflow: WorkflowDef,
        inputs: dict,
    ) -> None:
        self.events.append(("workflow_start", run_id, workflow.name, inputs))

    def on_workflow_end(self, *, record: RunRecord) -> None:
        self.events.append(("workflow_end", record.run_id, record.status.value))

    def on_step_start(
        self,
        *,
        run_id: str,
        step: StepDef,
        inputs: dict,
    ) -> None:
        self.events.append(("step_start", run_id, step.id, inputs))

    def on_step_end(
        self,
        *,
        run_id: str,
        step: StepDef,
        result: StepResult,
    ) -> None:
        self.events.append(
            (
                "step_end",
                run_id,
                step.id,
                result.status.value,
                result.cached,
                result.attempt,
                result.input_hash,
                result.output_hash,
            )
        )

    def flush(self) -> None:
        self.events.append(("flush",))


class _FakeContextManager:
    def __init__(self, payload: object) -> None:
        self.payload = payload
        self.closed = False

    def __enter__(self) -> object:
        return self.payload

    def __exit__(self, exc_type, exc, tb) -> None:
        self.closed = True
        return None


class FakeSpan:
    def __init__(self, name: str, input_data: dict | None, metadata: dict | None) -> None:
        self.name = name
        self.input_data = input_data
        self.metadata = metadata or {}
        self.updates: list[dict] = []

    def update(self, **kwargs) -> None:
        self.updates.append(kwargs)


class FakeLangfuseClient:
    def __init__(self) -> None:
        self.spans: list[FakeSpan] = []
        self.propagations: list[dict] = []
        self.flush_count = 0

    def start_as_current_observation(self, **kwargs) -> _FakeContextManager:
        span = FakeSpan(
            name=kwargs["name"],
            input_data=kwargs.get("input"),
            metadata=kwargs.get("metadata"),
        )
        self.spans.append(span)
        return _FakeContextManager(span)

    def propagate_attributes(self, **kwargs) -> _FakeContextManager:
        self.propagations.append(kwargs)
        return _FakeContextManager(kwargs)

    def flush(self) -> None:
        self.flush_count += 1


class TestLangfuseObserver:
    def test_workflow_engine_notifies_observer_for_success_and_cache(self, tmp_path) -> None:
        observer = RecordingObserver()
        cache = StepCache(os.path.join(tmp_path, "cache.db"))
        engine = WorkflowEngine(
            cache=cache,
            output_dir=os.path.join(tmp_path, "runs"),
            observer=observer,
        )
        engine.register("double", lambda x: {"doubled": x * 2})

        workflow = WorkflowDef(
            name="observer-test",
            version="1.0",
            steps=[StepDef(id="double_step", name="Double", function="double", inputs={"x": "$input.x"})],
        )

        first = engine.run(workflow, inputs={"x": 5})
        second = engine.run(workflow, inputs={"x": 5})

        first_step_end = [
            event for event in observer.events
            if event[:3] == ("step_end", first.run_id, "double_step")
        ][0]
        second_step_end = [
            event for event in observer.events
            if event[:3] == ("step_end", second.run_id, "double_step")
        ][0]

        assert first_step_end[3] == StepStatus.SUCCESS.value
        assert first_step_end[4] is False
        assert first_step_end[5] == 1
        assert first_step_end[6]
        assert first_step_end[7]

        assert second_step_end[3] == StepStatus.CACHED.value
        assert second_step_end[4] is True
        assert second_step_end[5] == 1
        assert second_step_end[6]
        assert second_step_end[7]

        assert observer.events.count(("flush",)) == 2

    def test_langfuse_observer_is_disabled_without_configuration(self, monkeypatch) -> None:
        monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
        monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
        monkeypatch.delenv("LANGFUSE_HOST", raising=False)

        observer = LangfuseObserver()

        workflow = WorkflowDef(name="wf", version="1.0", steps=[])
        record = RunRecord(
            run_id="run-disabled",
            workflow_name=workflow.name,
            workflow_version=workflow.version,
            status=StepStatus.SUCCESS,
            finished_at=datetime.utcnow(),
        )

        assert observer.enabled is False
        observer.on_workflow_start(run_id=record.run_id, workflow=workflow, inputs={})
        observer.on_workflow_end(record=record)
        observer.flush()

    def test_langfuse_observer_records_trace_and_step_metadata(self) -> None:
        client = FakeLangfuseClient()
        observer = LangfuseObserver(client=client)

        workflow = WorkflowDef(name="wf", version="1.0", steps=[])
        step = StepDef(id="s1", name="S1", function="noop")
        record = RunRecord(
            run_id="run-123",
            workflow_name=workflow.name,
            workflow_version=workflow.version,
            status=StepStatus.SUCCESS,
            finished_at=datetime.utcnow(),
        )
        result = StepResult(
            step_id=step.id,
            status=StepStatus.SUCCESS,
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
            duration_ms=12.5,
            input_hash="input-hash",
            output_hash="output-hash",
            output_data={"ok": True},
            attempt=2,
        )

        observer.on_workflow_start(run_id=record.run_id, workflow=workflow, inputs={"x": 1})
        observer.on_step_start(run_id=record.run_id, step=step, inputs={"x": 1})
        observer.on_step_end(run_id=record.run_id, step=step, result=result)
        observer.on_workflow_end(record=record)
        observer.flush()

        assert client.propagations == [{"trace_name": "run-123", "session_id": "run-123"}]
        assert [span.name for span in client.spans] == ["wf", "s1"]
        assert client.spans[1].updates[-1]["metadata"] == {
            "step_id": "s1",
            "status": StepStatus.SUCCESS.value,
            "input_hash": "input-hash",
            "output_hash": "output-hash",
            "cached": False,
            "attempt": 2,
            "duration_ms": 12.5,
        }
        assert client.flush_count == 1
