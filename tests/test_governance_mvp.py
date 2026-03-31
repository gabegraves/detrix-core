from __future__ import annotations

import os
import tempfile
from typing import Any

from detrix.core.governance import (
    Decision,
    GateContext,
    GovernanceGate,
    VerdictContract,
)
from detrix.core.models import RetryConfig, StepDef, StepStatus, WorkflowDef
from detrix.core.pipeline import WorkflowEngine
from detrix.runtime.audit import AuditLog


class MinValueGate(GovernanceGate):
    def __init__(self, minimum: int) -> None:
        self.minimum = minimum

    @property
    def gate_id(self) -> str:
        return "min_value"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, inputs: dict[str, Any], context: GateContext) -> VerdictContract:
        del context
        value = inputs["value"]
        decision = Decision.ACCEPT if value >= self.minimum else Decision.REJECT
        return VerdictContract(
            decision=decision,
            gate_id=self.gate_id,
            evidence={"value": value, "minimum": self.minimum},
            reason_codes=[] if decision == Decision.ACCEPT else ["value_below_minimum"],
            evaluator_version=self.version,
        )


class TestGovernanceMvp:
    def test_gate_accepts_and_persists_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            audit = AuditLog(os.path.join(tmp_dir, "audit.db"))
            engine = WorkflowEngine(
                audit=audit,
                output_dir=os.path.join(tmp_dir, "out"),
            )
            engine.register("produce", lambda: {"value": 7})
            engine.register_gate("s1", MinValueGate(minimum=5))

            workflow = WorkflowDef(
                name="governed-success",
                version="1.0",
                steps=[StepDef(id="s1", name="S1", function="produce")],
            )

            record = engine.run(workflow)

            assert record.status == StepStatus.SUCCESS
            assert record.step_results[0].gate_verdict is not None
            assert record.step_results[0].gate_verdict["decision"] == "accept"
            assert record.step_results[0].gate_verdict["gate_id"] == "min_value"

            run = audit.get_run(record.run_id)
            assert run is not None
            assert run["steps"][0]["gate_decision"] == "accept"
            assert run["steps"][0]["gate_id"] == "min_value"
            assert "value" in run["steps"][0]["gate_verdict_json"]

    def test_gate_rejection_fails_fast_without_retrying_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            calls = {"count": 0}
            audit = AuditLog(os.path.join(tmp_dir, "audit.db"))
            engine = WorkflowEngine(
                audit=audit,
                output_dir=os.path.join(tmp_dir, "out"),
            )

            def produce() -> dict[str, int]:
                calls["count"] += 1
                return {"value": 1}

            engine.register("produce", produce)
            engine.register_gate("s1", MinValueGate(minimum=5))

            workflow = WorkflowDef(
                name="governed-failure",
                version="1.0",
                steps=[
                    StepDef(
                        id="s1",
                        name="S1",
                        function="produce",
                        retry=RetryConfig(max_attempts=3, backoff_seconds=0.01),
                    ),
                    StepDef(
                        id="s2",
                        name="S2",
                        function="produce",
                        depends_on=["s1"],
                    ),
                ],
            )

            record = engine.run(workflow)

            assert calls["count"] == 1
            assert record.status == StepStatus.FAILED
            assert len(record.step_results) == 1
            assert record.step_results[0].status == StepStatus.FAILED
            assert record.step_results[0].attempt == 1
            assert record.step_results[0].gate_verdict is not None
            assert record.step_results[0].gate_verdict["decision"] == "reject"
            assert "Governance gate" in (record.step_results[0].error or "")

            run = audit.get_run(record.run_id)
            assert run is not None
            assert run["steps"][0]["gate_decision"] == "reject"
            assert run["steps"][0]["attempt"] == 1
