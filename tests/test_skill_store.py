from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from detrix.core.skill_registry import DeterministicTool, SkillDefinition, SkillRouting
from detrix.runtime.skill_store import SkillStore


def test_register_tool_and_get_tools_for_domain(tmp_path) -> None:
    store = SkillStore(str(tmp_path / "skills.db"))
    store.register_tool(_tool("rietveld_rwp_calc", domain="xrd"))
    store.register_tool(_tool("timezone_calc", domain="calendar"))

    tools = store.get_tools_for_domain("xrd")

    assert [tool.tool_id for tool in tools] == ["rietveld_rwp_calc"]
    assert tools[0].output_schema["properties"]["rwp"]["type"] == "number"


def test_duplicate_tool_id_raises(tmp_path) -> None:
    store = SkillStore(str(tmp_path / "skills.db"))
    tool = _tool("rietveld_rwp_calc")
    store.register_tool(tool)

    with pytest.raises(sqlite3.IntegrityError):
        store.register_tool(tool)


def test_register_skill_and_get_skill(tmp_path) -> None:
    store = SkillStore(str(tmp_path / "skills.db"))
    skill = _skill("xrd-rwp-validation", status="validated")

    store.register_skill(skill)
    got = store.get_skill("xrd-rwp-validation")

    assert got is not None
    assert got.skill_id == skill.skill_id
    assert got.status == "validated"
    assert got.created_at == skill.created_at


def test_get_missing_skill_returns_none(tmp_path) -> None:
    store = SkillStore(str(tmp_path / "skills.db"))

    assert store.get_skill("missing") is None


def test_list_skills_filters_by_domain_and_status(tmp_path) -> None:
    store = SkillStore(str(tmp_path / "skills.db"))
    store.register_skill(_skill("xrd-rwp-validation", domain="xrd", status="active"))
    store.register_skill(_skill("xrd-phase-id", domain="xrd", status="candidate"))
    store.register_skill(_skill("calendar-timezone", domain="calendar", status="active"))

    active_xrd = store.list_skills(domain="xrd", status="active")

    assert [skill.skill_id for skill in active_xrd] == ["xrd-rwp-validation"]


def test_duplicate_skill_id_raises(tmp_path) -> None:
    store = SkillStore(str(tmp_path / "skills.db"))
    skill = _skill("xrd-rwp-validation")
    store.register_skill(skill)

    with pytest.raises(sqlite3.IntegrityError):
        store.register_skill(skill)


def test_add_routing_and_find_exact_intent(tmp_path) -> None:
    store = SkillStore(str(tmp_path / "skills.db"))
    routing = SkillRouting(
        intent_pattern="validate rwp",
        skill_id="xrd-rwp-validation",
    )
    store.add_routing(routing)

    found = store.find_routing("  Validate   RWP ")

    assert found == routing


def test_find_routing_uses_substring_match(tmp_path) -> None:
    store = SkillStore(str(tmp_path / "skills.db"))
    store.add_routing(
        SkillRouting(
            intent_pattern="validate rwp",
            skill_id="xrd-rwp-validation",
        )
    )

    found = store.find_routing("please validate rwp for the refinement")

    assert found is not None
    assert found.skill_id == "xrd-rwp-validation"


def test_add_routing_upserts_by_intent_pattern(tmp_path) -> None:
    store = SkillStore(str(tmp_path / "skills.db"))
    store.add_routing(
        SkillRouting(
            intent_pattern="validate rwp",
            skill_id="old-skill",
            confidence_threshold=0.75,
        )
    )
    store.add_routing(
        SkillRouting(
            intent_pattern="validate rwp",
            skill_id="xrd-rwp-validation",
            confidence_threshold=0.9,
        )
    )

    found = store.find_routing("validate rwp")

    assert found is not None
    assert found.skill_id == "xrd-rwp-validation"
    assert found.confidence_threshold == 0.9


def test_find_routing_returns_none_for_unknown_or_empty_intent(tmp_path) -> None:
    store = SkillStore(str(tmp_path / "skills.db"))
    store.add_routing(
        SkillRouting(
            intent_pattern="validate rwp",
            skill_id="xrd-rwp-validation",
        )
    )

    assert store.find_routing("unrelated task") is None
    assert store.find_routing("   ") is None


def test_schema_indexes_exist(tmp_path) -> None:
    store = SkillStore(str(tmp_path / "skills.db"))

    with sqlite3.connect(store.db_path) as conn:
        indexes = {
            row[1]
            for row in conn.execute(
                "SELECT type, name FROM sqlite_master WHERE type = 'index'"
            ).fetchall()
        }

    assert "idx_tools_domain" in indexes
    assert "idx_skills_domain" in indexes
    assert "idx_skills_status" in indexes
    assert "idx_skills_skill_id" in indexes


def _tool(tool_id: str, *, domain: str = "xrd") -> DeterministicTool:
    return DeterministicTool(
        tool_id=tool_id,
        script_path=f"tools/{domain}/{tool_id}.py",
        input_schema={"type": "object"},
        output_schema={"type": "object", "properties": {"rwp": {"type": "number"}}},
        domain=domain,
        version="1.0.0",
    )


def _skill(
    skill_id: str,
    *,
    domain: str = "xrd",
    status: str = "candidate",
) -> SkillDefinition:
    return SkillDefinition(
        skill_id=skill_id,
        name=skill_id.replace("-", " ").title(),
        description="Use this deterministic skill when the route matches.",
        triggers=["validate rwp"],
        deterministic_tool_ids=["rietveld_rwp_calc"],
        test_intents=["validate the Rwp for this refinement"],
        domain=domain,
        version="0.1.0",
        created_from_trajectory_id="traj-001",
        created_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
        status=status,
    )
