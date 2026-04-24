from __future__ import annotations

from datetime import datetime, timezone

from detrix.core.skill_registry import DeterministicTool, SkillDefinition, SkillRouting


def test_deterministic_tool_model_round_trips_json() -> None:
    tool = DeterministicTool(
        tool_id="rietveld_rwp_calc",
        script_path="tools/xrd/rietveld_rwp.py",
        input_schema={"type": "object", "properties": {"pattern": {"type": "array"}}},
        output_schema={"type": "object", "properties": {"rwp": {"type": "number"}}},
        domain="xrd",
        version="1.0.0",
    )

    restored = DeterministicTool.model_validate_json(tool.model_dump_json())

    assert restored.tool_id == "rietveld_rwp_calc"
    assert restored.output_schema["properties"]["rwp"]["type"] == "number"


def test_skill_definition_defaults_to_candidate_status() -> None:
    created_at = datetime(2026, 4, 24, tzinfo=timezone.utc)
    skill = SkillDefinition(
        skill_id="xrd-rwp-validation",
        name="XRD Rwp Validation",
        description="Use when validating Rwp values from refinement output.",
        triggers=["validate rwp", "check refinement quality"],
        deterministic_tool_ids=["rietveld_rwp_calc"],
        test_intents=["validate the Rwp for this refinement"],
        domain="xrd",
        version="0.1.0",
        created_at=created_at,
    )

    assert skill.status == "candidate"
    assert skill.created_from_trajectory_id is None
    assert skill.created_at == created_at


def test_skill_routing_default_threshold() -> None:
    routing = SkillRouting(
        intent_pattern="validate rwp",
        skill_id="xrd-rwp-validation",
    )

    assert routing.confidence_threshold == 0.8
