"""Optional workflow observer with a Langfuse backend."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from detrix.core.models import RunRecord, StepDef, StepResult, WorkflowDef

_LANGFUSE_CLIENT_CLASS: Any | None = None
_LANGFUSE_OTEL_ATTRIBUTES: Any | None = None

try:
    from langfuse import Langfuse as _ImportedLangfuseClient
    from langfuse._client.attributes import (
        LangfuseOtelSpanAttributes as _ImportedLangfuseOtelSpanAttributes,
    )
except ImportError:  # pragma: no cover - exercised via graceful fallback tests
    pass
else:
    _LANGFUSE_CLIENT_CLASS = _ImportedLangfuseClient
    _LANGFUSE_OTEL_ATTRIBUTES = _ImportedLangfuseOtelSpanAttributes


class WorkflowObserver(ABC):
    """Generic workflow lifecycle observer interface."""

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """Whether the observer can emit events."""

    @abstractmethod
    def on_workflow_start(
        self,
        *,
        run_id: str,
        workflow: WorkflowDef,
        inputs: dict[str, Any],
    ) -> None:
        """Called before workflow execution begins."""

    @abstractmethod
    def on_workflow_end(self, *, record: RunRecord) -> None:
        """Called after workflow execution finishes."""

    @abstractmethod
    def on_step_start(
        self,
        *,
        run_id: str,
        step: StepDef,
        inputs: dict[str, Any],
    ) -> None:
        """Called before step execution begins."""

    @abstractmethod
    def on_step_end(
        self,
        *,
        run_id: str,
        step: StepDef,
        result: StepResult,
    ) -> None:
        """Called after step execution finishes."""

    @abstractmethod
    def flush(self) -> None:
        """Force any buffered events to be sent."""


class NoOpWorkflowObserver(WorkflowObserver):
    """Observer implementation that intentionally does nothing."""

    @property
    def enabled(self) -> bool:
        return False

    def on_workflow_start(
        self,
        *,
        run_id: str,
        workflow: WorkflowDef,
        inputs: dict[str, Any],
    ) -> None:
        del run_id, workflow, inputs

    def on_workflow_end(self, *, record: RunRecord) -> None:
        del record

    def on_step_start(
        self,
        *,
        run_id: str,
        step: StepDef,
        inputs: dict[str, Any],
    ) -> None:
        del run_id, step, inputs

    def on_step_end(
        self,
        *,
        run_id: str,
        step: StepDef,
        result: StepResult,
    ) -> None:
        del run_id, step, result

    def flush(self) -> None:
        return None


class LangfuseObserver(WorkflowObserver):
    """Optional Langfuse-backed observer for workflow runs and steps."""

    def __init__(self, client: Any | None = None) -> None:
        self._client = client
        self._workflow_context_manager: Any | None = None
        self._workflow_span: Any | None = None
        self._propagation_context_manager: Any | None = None
        self._step_contexts: dict[tuple[str, str], tuple[Any, Any]] = {}
        self._enabled = client is not None

        if client is not None:
            return

        if _LANGFUSE_CLIENT_CLASS is None:
            return

        required_env = (
            os.getenv("LANGFUSE_PUBLIC_KEY"),
            os.getenv("LANGFUSE_SECRET_KEY"),
            os.getenv("LANGFUSE_HOST"),
        )
        if not all(required_env):
            return

        try:
            client_class = cast(Any, _LANGFUSE_CLIENT_CLASS)
            self._client = client_class()
            self._enabled = True
        except Exception:
            self._client = None
            self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    def on_workflow_start(
        self,
        *,
        run_id: str,
        workflow: WorkflowDef,
        inputs: dict[str, Any],
    ) -> None:
        if not self.enabled:
            return

        client = self._client
        if client is None:
            return

        try:
            self._workflow_context_manager, self._workflow_span = self._start_observation(
                name=workflow.name,
                input_data=inputs,
                metadata={
                    "run_id": run_id,
                    "workflow_name": workflow.name,
                    "workflow_version": workflow.version,
                },
            )
            if hasattr(client, "propagate_attributes"):
                self._propagation_context_manager = client.propagate_attributes(
                    trace_name=run_id,
                    session_id=run_id,
                )
                self._enter_context(self._propagation_context_manager)
            else:
                self._set_trace_attributes(span=self._workflow_span, run_id=run_id)
        except Exception:
            self._disable()

    def on_workflow_end(self, *, record: RunRecord) -> None:
        if not self.enabled:
            return

        try:
            if self._workflow_span is not None:
                self._workflow_span.update(
                    output={
                        "status": record.status.value,
                        "step_ids": [result.step_id for result in record.step_results],
                    },
                    metadata={
                        "run_id": record.run_id,
                        "workflow_name": record.workflow_name,
                        "workflow_version": record.workflow_version,
                        "status": record.status.value,
                        "duration_ms": record.duration_ms,
                        "step_count": len(record.step_results),
                    },
                    status_message=record.status.value,
                )
        except Exception:
            self._disable()
        finally:
            self._close_context(self._propagation_context_manager)
            self._close_context(self._workflow_context_manager)
            self._propagation_context_manager = None
            self._workflow_context_manager = None
            self._workflow_span = None
            self._step_contexts.clear()

    def on_step_start(
        self,
        *,
        run_id: str,
        step: StepDef,
        inputs: dict[str, Any],
    ) -> None:
        if not self.enabled:
            return

        try:
            context_manager, span = self._start_observation(
                name=step.id,
                input_data=inputs,
                metadata={
                    "step_id": step.id,
                    "function": step.function,
                },
            )
            self._step_contexts[(run_id, step.id)] = (context_manager, span)
        except Exception:
            self._disable()

    def on_step_end(
        self,
        *,
        run_id: str,
        step: StepDef,
        result: StepResult,
    ) -> None:
        if not self.enabled:
            return

        client = self._client
        if client is None:
            return

        key = (run_id, step.id)
        context = self._step_contexts.pop(key, None)
        if context is None:
            return

        context_manager, span = context
        metadata = {
            "step_id": result.step_id,
            "status": result.status.value,
            "input_hash": result.input_hash,
            "output_hash": result.output_hash,
            "cached": result.cached,
            "attempt": result.attempt,
            "duration_ms": result.duration_ms,
        }
        if result.error:
            metadata["error"] = result.error

        try:
            span.update(
                output=result.output_data or None,
                metadata=metadata,
                status_message=result.error or result.status.value,
            )
        except Exception:
            self._disable()
        finally:
            self._close_context(context_manager)

    def flush(self) -> None:
        if not self.enabled:
            return

        client = self._client
        if client is None:
            return

        try:
            client.flush()
        except Exception:
            self._disable()

    def _disable(self) -> None:
        self._enabled = False
        self._client = None
        self._workflow_context_manager = None
        self._workflow_span = None
        self._propagation_context_manager = None
        self._step_contexts.clear()

    def _start_observation(
        self,
        *,
        name: str,
        input_data: Any | None,
        metadata: dict[str, Any],
    ) -> tuple[Any, Any]:
        client = self._client
        if client is None:
            raise RuntimeError("Langfuse client is not initialized")

        context_manager = client.start_as_current_observation(
            name=name,
            input=input_data,
            metadata=metadata,
        )
        span = self._enter_context(context_manager)
        return context_manager, span

    @staticmethod
    def _enter_context(context_manager: Any) -> Any:
        return context_manager.__enter__()

    @staticmethod
    def _close_context(context_manager: Any | None) -> None:
        if context_manager is None:
            return
        context_manager.__exit__(None, None, None)

    @staticmethod
    def _set_trace_attributes(*, span: Any, run_id: str) -> None:
        if _LANGFUSE_OTEL_ATTRIBUTES is None:
            return

        otel_span = getattr(span, "_otel_span", None)
        if otel_span is None:
            return

        attributes = cast(Any, _LANGFUSE_OTEL_ATTRIBUTES)
        otel_span.set_attribute(attributes.TRACE_NAME, run_id)
        otel_span.set_attribute(attributes.TRACE_SESSION_ID, run_id)
