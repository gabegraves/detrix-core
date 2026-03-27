"""Minimal YAML workflow engine with step-level durability.

Parses YAML workflow definitions, executes steps in topological order,
caches outputs by content hash, and records everything to an audit log.
"""

from __future__ import annotations

import importlib
import json
import re
import time
from datetime import datetime
from graphlib import TopologicalSorter
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import yaml

from detrix.core.cache import StepCache, _stable_hash
from detrix.core.models import (
    RetryConfig,
    RunRecord,
    StepDef,
    StepResult,
    StepStatus,
    WorkflowDef,
)
from detrix.core.types import StepExecutionError
from detrix.runtime.audit import AuditLog


# ---------------------------------------------------------------------------
# YAML parsing
# ---------------------------------------------------------------------------


def parse_workflow(path: str) -> WorkflowDef:
    """Parse a YAML file into a WorkflowDef."""
    with open(path) as f:
        raw = yaml.safe_load(f)

    steps = []
    for s in raw.get("steps", []):
        retry_raw = s.get("retry", {})
        retry = RetryConfig(**retry_raw) if retry_raw else RetryConfig()
        steps.append(
            StepDef(
                id=s["id"],
                name=s.get("name", s["id"]),
                function=s["function"],
                inputs=s.get("inputs", {}),
                outputs=s.get("outputs", []),
                depends_on=s.get("depends_on", []),
                retry=retry,
                timeout_seconds=s.get("timeout_seconds"),
                approval_required=s.get("approval_required", False),
            )
        )

    return WorkflowDef(
        name=raw["name"],
        version=raw.get("version", "1.0"),
        description=raw.get("description", ""),
        steps=steps,
        metadata=raw.get("metadata", {}),
    )


# ---------------------------------------------------------------------------
# DAG utilities
# ---------------------------------------------------------------------------

_VAR_RE = re.compile(r"\$(\w+)\.(\w+)")


def _topo_order(steps: list[StepDef]) -> list[str]:
    """Return step IDs in topological execution order."""
    graph: dict[str, set[str]] = {}
    for step in steps:
        graph[step.id] = set(step.depends_on)
    ts = TopologicalSorter(graph)
    return list(ts.static_order())


def _resolve_inputs(
    raw_inputs: Dict[str, str],
    context: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Resolve $step.key references against completed step outputs."""
    resolved: Dict[str, Any] = {}
    for key, val in raw_inputs.items():
        if isinstance(val, str):
            m = _VAR_RE.fullmatch(val)
            if m:
                src_step, src_key = m.group(1), m.group(2)
                if src_step in context and src_key in context[src_step]:
                    resolved[key] = context[src_step][src_key]
                else:
                    raise ValueError(
                        f"Unresolved reference {val}: "
                        f"step '{src_step}' output '{src_key}' not found"
                    )
                continue
        resolved[key] = val
    return resolved


# ---------------------------------------------------------------------------
# Function resolution
# ---------------------------------------------------------------------------


def _resolve_function(dotted_path: str) -> Callable:
    """Import a callable from a dotted path like 'mypackage.steps.process'."""
    parts = dotted_path.rsplit(".", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid function path: {dotted_path}")
    module_path, func_name = parts
    module = importlib.import_module(module_path)
    func = getattr(module, func_name)
    if not callable(func):
        raise TypeError(f"{dotted_path} is not callable")
    return func


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class WorkflowEngine:
    """Execute YAML-defined workflows with caching and audit."""

    def __init__(
        self,
        cache: Optional[StepCache] = None,
        audit: Optional[AuditLog] = None,
        output_dir: str = "outputs/workflow",
        verbose: bool = False,
    ):
        self.cache = cache
        self.audit = audit
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.verbose = verbose
        self._registry: Dict[str, Callable] = {}

    def register(self, name: str, func: Callable) -> None:
        """Register a step function by name (alternative to dotted imports)."""
        self._registry[name] = func

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"[detrix] {msg}")

    def _get_func(self, dotted_path: str) -> Callable:
        if dotted_path in self._registry:
            return self._registry[dotted_path]
        return _resolve_function(dotted_path)

    def _execute_step(
        self,
        step: StepDef,
        inputs: Dict[str, Any],
        run_id: str,
    ) -> StepResult:
        """Execute a single step with retry, caching, and audit."""

        # Check cache
        if self.cache:
            cached = self.cache.get(step.id, inputs)
            if cached is not None:
                now = datetime.utcnow()
                self._log(f"  CACHED  {step.id}")
                result = StepResult(
                    step_id=step.id,
                    status=StepStatus.CACHED,
                    started_at=now,
                    finished_at=now,
                    duration_ms=0.0,
                    input_hash=self.cache.input_hash(inputs),
                    output_hash=self.cache.output_hash(cached),
                    output_data=cached,
                    cached=True,
                )
                if self.audit:
                    self.audit.record_step(run_id, result)
                return result

        func = self._get_func(step.function)
        last_error: Optional[str] = None

        for attempt in range(1, step.retry.max_attempts + 1):
            started = datetime.utcnow()
            t0 = time.monotonic()
            try:
                self._log(f"  RUN     {step.id} (attempt {attempt})")
                output = func(**inputs)
                if not isinstance(output, dict):
                    output = {"result": output}
                elapsed = (time.monotonic() - t0) * 1000
                finished = datetime.utcnow()

                ih = self.cache.input_hash(inputs) if self.cache else _stable_hash(inputs)
                oh = self.cache.output_hash(output) if self.cache else _stable_hash(output)

                if self.cache:
                    self.cache.put(step.id, inputs, output)

                out_file = self.output_dir / f"{run_id}" / f"{step.id}.json"
                out_file.parent.mkdir(parents=True, exist_ok=True)
                tmp = out_file.with_suffix(".tmp")
                tmp.write_text(json.dumps(output, default=str, indent=2))
                tmp.rename(out_file)

                result = StepResult(
                    step_id=step.id,
                    status=StepStatus.SUCCESS,
                    started_at=started,
                    finished_at=finished,
                    duration_ms=elapsed,
                    input_hash=ih,
                    output_hash=oh,
                    output_data=output,
                    attempt=attempt,
                )
                if self.audit:
                    self.audit.record_step(run_id, result)
                return result

            except Exception as e:
                # Wrap user-code failures so the outer run() loop can
                # distinguish "step function raised" from governance errors
                # (GovernanceError) which must propagate unwrapped.
                wrapped = StepExecutionError(step.id, e)
                last_error = str(e)
                elapsed = (time.monotonic() - t0) * 1000
                self._log(f"  FAIL    {step.id} attempt {attempt}: {last_error}")
                if attempt < step.retry.max_attempts:
                    wait = step.retry.backoff_seconds * (
                        step.retry.backoff_multiplier ** (attempt - 1)
                    )
                    time.sleep(wait)
                del wrapped  # held only to document intent; last_error is used below

        # All retries exhausted
        finished = datetime.utcnow()
        result = StepResult(
            step_id=step.id,
            status=StepStatus.FAILED,
            started_at=started,
            finished_at=finished,
            duration_ms=(time.monotonic() - t0) * 1000,
            input_hash=_stable_hash(inputs),
            error=last_error,
            attempt=step.retry.max_attempts,
        )
        if self.audit:
            self.audit.record_step(run_id, result)
        return result

    def run(
        self,
        workflow: WorkflowDef,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> RunRecord:
        """Execute a full workflow in topological order."""

        inputs = inputs or {}
        record = RunRecord(
            workflow_name=workflow.name,
            workflow_version=workflow.version,
            status=StepStatus.RUNNING,
            inputs=inputs,
        )
        if self.audit:
            self.audit.record_run_start(record)

        self._log(f"RUN {workflow.name} v{workflow.version} [{record.run_id}]")

        step_map = {s.id: s for s in workflow.steps}
        context: Dict[str, Dict[str, Any]] = {"input": inputs}

        order = _topo_order(workflow.steps)
        for step_id in order:
            step = step_map[step_id]

            try:
                resolved = _resolve_inputs(step.inputs, context)
            except ValueError as e:
                record.status = StepStatus.FAILED
                record.finished_at = datetime.utcnow()
                record.step_results.append(
                    StepResult(
                        step_id=step_id,
                        status=StepStatus.FAILED,
                        started_at=datetime.utcnow(),
                        finished_at=datetime.utcnow(),
                        duration_ms=0,
                        error=str(e),
                    )
                )
                if self.audit:
                    self.audit.record_run_end(record)
                return record

            # GOVERNANCE INTEGRATION POINT: when GovernanceError is added,
            # wrap the _execute_step call in a separate try/except for
            # GovernanceError BEFORE this call so governance failures bypass
            # step retry logic and propagate directly to the caller.
            result = self._execute_step(step, resolved, record.run_id)
            record.step_results.append(result)

            if result.status == StepStatus.FAILED:
                self._log(f"  ABORT   workflow failed at step {step_id}")
                record.status = StepStatus.FAILED
                record.finished_at = datetime.utcnow()
                if self.audit:
                    self.audit.record_run_end(record)
                return record

            context[step_id] = result.output_data

        record.status = StepStatus.SUCCESS
        record.finished_at = datetime.utcnow()
        self._log(
            f"DONE  {workflow.name} [{record.run_id}] "
            f"{record.duration_ms:.0f}ms"
        )
        if self.audit:
            self.audit.record_run_end(record)
        return record

    def run_from_yaml(
        self,
        yaml_path: str,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> RunRecord:
        """Parse a YAML file and execute the workflow."""
        workflow = parse_workflow(yaml_path)
        return self.run(workflow, inputs)
