"""Replay-gated promotion checks for OpenClaw readability gates."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from detrix.core.governance import GateContext
from detrix.openclaw.gates import OpenClawGovernanceGate


@dataclass(frozen=True)
class ReplayCaseResult:
    """Result for one frozen replay case."""

    case_id: str
    expected_decision: str
    actual_decision: str
    expected_reason_codes: list[str]
    actual_reason_codes: list[str]
    passed: bool


@dataclass(frozen=True)
class ReplayReport:
    """Promotion gate report for a frozen OpenClaw replay suite."""

    total: int
    passed: int
    failed: int
    regressions: int
    before_after_delta: dict[str, Any] = field(default_factory=dict)
    cases: list[ReplayCaseResult] = field(default_factory=list)

    @property
    def promotion_allowed(self) -> bool:
        return self.regressions == 0

    def model_dump(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "regressions": self.regressions,
            "promotion_allowed": self.promotion_allowed,
            "before_after_delta": self.before_after_delta,
            "cases": [case.__dict__ for case in self.cases],
        }


def run_replay_suite(
    fixture_path: str | Path,
    *,
    config: dict[str, Any] | None = None,
    gate: OpenClawGovernanceGate | None = None,
) -> ReplayReport:
    """Run frozen OpenClaw failures through the current gate suite."""
    path = Path(fixture_path)
    suite = gate or OpenClawGovernanceGate()
    cases: list[ReplayCaseResult] = []
    with path.open(encoding="utf-8") as file:
        for line_index, line in enumerate(file):
            raw = line.strip()
            if not raw:
                continue
            payload = json.loads(raw)
            case_id = str(payload.get("case_id") or f"case-{line_index}")
            message = str(payload.get("message") or payload.get("agent_output") or "")
            expected_decision = str(payload["expected_decision"]).lower()
            expected_reason_codes = [str(code) for code in payload.get("expected_reason_codes", [])]
            context = GateContext(
                run_id=f"openclaw-replay-{case_id}",
                step_index=line_index,
                prior_verdicts=[],
                config=config or {},
            )
            verdict = suite.evaluate({"message": message}, context)
            actual_decision = verdict.decision.value
            actual_reason_codes = verdict.reason_codes
            reason_match = all(code in actual_reason_codes for code in expected_reason_codes)
            passed = actual_decision == expected_decision and reason_match
            cases.append(
                ReplayCaseResult(
                    case_id=case_id,
                    expected_decision=expected_decision,
                    actual_decision=actual_decision,
                    expected_reason_codes=expected_reason_codes,
                    actual_reason_codes=actual_reason_codes,
                    passed=passed,
                )
            )
    failed = [case for case in cases if not case.passed]
    return ReplayReport(
        total=len(cases),
        passed=len(cases) - len(failed),
        failed=len(failed),
        regressions=len(failed),
        before_after_delta={
            "expected_failures_preserved": len(cases) - len(failed),
            "unexpected_decision_changes": len(failed),
        },
        cases=cases,
    )
