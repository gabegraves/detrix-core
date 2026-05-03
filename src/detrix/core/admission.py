"""Portable admission routing for governed trajectories."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from detrix.core.trajectory import GovernedTrajectory

TrainingRoute = Literal["sft", "dpo", "grpo", "eval_only"]
ReplayStatus = Literal["passed", "failed", "pending"]

_CAUTION_TO_DPO = {
    "needs_chunking",
    "paragraph_density_exceeded",
    "needs_reformat",
    "inline_bullet_anti_pattern",
    "apology_as_content",
    "low_readability_advisory",
}


@dataclass(frozen=True)
class AdmissionResult:
    """Computed admission fields for a governed trajectory."""

    training_route: TrainingRoute
    replay_status: ReplayStatus
    promotion_eligible: bool
    rejection_type: str | None
    reason_codes: list[str]


class AdmissionBuilder:
    """Populate portable admission fields from governance verdicts."""

    @staticmethod
    def compute_training_route(verdicts: list[dict[str, Any]]) -> TrainingRoute:
        flattened = _flatten_verdicts(verdicts)
        decisions = {_decision(verdict) for verdict in flattened}
        if decisions & {"reject", "request_more_data", "unknown"}:
            return "eval_only"
        reason_codes = {
            str(reason_code)
            for verdict in flattened
            for reason_code in verdict.get("reason_codes", [])
        }
        if "caution" in decisions or reason_codes & _CAUTION_TO_DPO:
            return "dpo"
        return "sft"

    @staticmethod
    def compute_admission(
        trajectory: GovernedTrajectory,
        *,
        replay_status: ReplayStatus = "pending",
    ) -> GovernedTrajectory:
        result = AdmissionBuilder.compute_result(trajectory.verdicts, replay_status=replay_status)
        updates: dict[str, Any] = {
            "training_route": result.training_route,
            "replay_status": result.replay_status,
            "promotion_eligible": result.promotion_eligible,
        }
        if trajectory.rejection_type is None and result.rejection_type is not None:
            updates["rejection_type"] = result.rejection_type
        return trajectory.model_copy(update=updates)

    @staticmethod
    def compute_result(
        verdicts: list[dict[str, Any]],
        *,
        replay_status: ReplayStatus = "pending",
    ) -> AdmissionResult:
        flattened = _flatten_verdicts(verdicts)
        route = AdmissionBuilder.compute_training_route(verdicts)
        reason_codes = [
            str(reason_code)
            for verdict in flattened
            for reason_code in verdict.get("reason_codes", [])
        ]
        rejection_type = next(
            (
                str(verdict["rejection_type"])
                for verdict in flattened
                if verdict.get("rejection_type")
            ),
            None,
        )
        if route == "eval_only" and rejection_type is None:
            rejection_type = "output_quality"
        promotion_eligible = route == "sft" and replay_status == "passed"
        return AdmissionResult(
            training_route=route,
            replay_status=replay_status,
            promotion_eligible=promotion_eligible,
            rejection_type=rejection_type,
            reason_codes=reason_codes,
        )


def _decision(verdict: dict[str, Any]) -> str:
    return str(verdict.get("decision", "unknown")).lower()


def _flatten_verdicts(verdicts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for verdict in verdicts:
        flattened.append(verdict)
        evidence = verdict.get("evidence", {})
        if isinstance(evidence, dict):
            child_verdicts = evidence.get("child_verdicts", [])
            if isinstance(child_verdicts, list):
                flattened.extend(
                    child for child in child_verdicts if isinstance(child, dict)
                )
    return flattened
