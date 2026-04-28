import pytest

from detrix.agentxrd.promotion_packet import (
    AgentXRDPromotionMetrics,
    build_promotion_packet,
)


def test_promotion_packet_blocks_when_safety_metrics_are_clean_but_no_sft_positive():
    packet = build_promotion_packet(
        metrics=AgentXRDPromotionMetrics(
            row_count=20,
            wrong_accept_count=0,
            support_only_accept_violation_count=0,
            accept_ineligible_accept_violation_count=0,
            truth_blocked_positive_count=0,
            provisional_positive_count=0,
            sft_positive_count=0,
        )
    )

    assert packet.promote is False
    assert "no_sft_positive_rows" in packet.block_reasons


def test_promotion_packet_fails_closed_on_missing_metric():
    with pytest.raises(ValueError, match="missing required safety metric"):
        AgentXRDPromotionMetrics.model_validate(
            {
                "row_count": 20,
                "wrong_accept_count": 0,
                "support_only_accept_violation_count": 0,
                "accept_ineligible_accept_violation_count": 0,
                "truth_blocked_positive_count": 0,
                "sft_positive_count": 0,
            }
        )
