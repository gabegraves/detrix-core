from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


class AgentXRDPromotionMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row_count: int
    wrong_accept_count: int
    support_only_accept_violation_count: int
    accept_ineligible_accept_violation_count: int
    truth_blocked_positive_count: int
    provisional_positive_count: int
    sft_positive_count: int

    @model_validator(mode="before")
    @classmethod
    def require_all_metrics(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        required = set(cls.model_fields)
        missing = sorted(required - set(data))
        if missing:
            raise ValueError(f"missing required safety metric: {', '.join(missing)}")
        return data


class AgentXRDPromotionPacket(BaseModel):
    schema_version: str = "agentxrd_promotion_packet_v0.1"
    metrics: AgentXRDPromotionMetrics
    promote: bool
    block_reasons: list[str]
    deterministic_gates_authoritative: bool = True


def build_promotion_packet(metrics: AgentXRDPromotionMetrics) -> AgentXRDPromotionPacket:
    block_reasons: list[str] = []
    if metrics.wrong_accept_count != 0:
        block_reasons.append("wrong_accept_count_nonzero")
    if metrics.support_only_accept_violation_count != 0:
        block_reasons.append("support_only_accept_violation")
    if metrics.accept_ineligible_accept_violation_count != 0:
        block_reasons.append("accept_ineligible_accept_violation")
    if metrics.truth_blocked_positive_count != 0:
        block_reasons.append("truth_blocked_positive")
    if metrics.provisional_positive_count != 0:
        block_reasons.append("provisional_positive")
    if metrics.sft_positive_count <= 0:
        block_reasons.append("no_sft_positive_rows")
    return AgentXRDPromotionPacket(
        metrics=metrics,
        promote=not block_reasons,
        block_reasons=block_reasons,
    )
