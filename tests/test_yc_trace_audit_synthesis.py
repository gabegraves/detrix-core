from __future__ import annotations

from pathlib import Path

from detrix.yc_trace_audit.schema import AgentFinding, AuditUnit, ReviewReport
from detrix.yc_trace_audit.synthesis import render_playbook


def _sample_unit(unit_id: str, project_id: str) -> AuditUnit:
    return AuditUnit(
        unit_id=unit_id,
        project_id=project_id,
        source_ids=[f"source-{unit_id}"],
        intent_summary=f"Intent for {unit_id}",
        outcome_summary=f"Outcome for {unit_id}",
        goal_doc_paths=[Path(f"/tmp/{project_id}/AGENTS.md")],
    )


def _sample_finding(finding_id: str, unit_ids: list[str], distance_to_goal: str = "closed") -> AgentFinding:
    return AgentFinding(
        finding_id=finding_id,
        role="success_patterns",
        unit_ids=unit_ids,
        project_id="detrix-core",
        claim="Closed with durable governed admission evidence",
        evidence=[f"unit:{unit_ids[0]}", "session:test"],
        distance_to_goal=distance_to_goal,  # type: ignore[arg-type]
        confidence="high",
        mental_model="Admission Boundary Is the Detrix Product Signal",
    )


def _sample_review_report(passed: bool) -> ReviewReport:
    return ReviewReport(
        passed=passed,
        total_units=1,
        covered_units=1 if passed else 0,
        uncovered_unit_ids=[] if passed else ["u1"],
        rejected_finding_ids=[] if passed else ["f1"],
        accepted_finding_ids=["f1"] if passed else [],
    )


def test_render_playbook_requires_passing_review() -> None:
    markdown = render_playbook(
        units=[_sample_unit("u1", "detrix-core")],
        findings=[_sample_finding("f1", ["u1"])],
        review_report=_sample_review_report(passed=False),
    )

    assert "SYNTHESIS BLOCKED" in markdown


def test_render_playbook_contains_required_sections() -> None:
    markdown = render_playbook(
        units=[_sample_unit("u1", "detrix-core")],
        findings=[_sample_finding("f1", ["u1"], distance_to_goal="closed")],
        review_report=_sample_review_report(passed=True),
    )

    assert "## What Works" in markdown
    assert "## What Fails" in markdown
    assert "## Distance to Goals" in markdown
    assert "## Product Direction" in markdown
    assert "## Recommended Demo Sprint Process" in markdown
    assert "## Evidence Appendix" in markdown
