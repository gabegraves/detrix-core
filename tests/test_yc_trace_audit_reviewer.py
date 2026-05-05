from __future__ import annotations

from pathlib import Path

from detrix.yc_trace_audit.reviewer import review_findings
from detrix.yc_trace_audit.schema import AgentFinding, AuditUnit


def _sample_unit(unit_id: str, project_id: str) -> AuditUnit:
    return AuditUnit(
        unit_id=unit_id,
        project_id=project_id,
        source_ids=[f"source-{unit_id}"],
        intent_summary=f"Intent for {unit_id}",
        outcome_summary=f"Outcome for {unit_id}",
        goal_doc_paths=[Path(f"/tmp/{project_id}/AGENTS.md")],
    )


def _sample_finding(
    finding_id: str,
    unit_ids: list[str],
    evidence: list[str] | None = None,
    distance_to_goal: str = "closed",
) -> AgentFinding:
    return AgentFinding(
        finding_id=finding_id,
        role="success_patterns",
        unit_ids=unit_ids,
        project_id="detrix-core",
        claim="Closed with durable evidence",
        evidence=evidence if evidence is not None else [f"unit:{unit_ids[0]}", "session:test"],
        distance_to_goal=distance_to_goal,  # type: ignore[arg-type]
        confidence="high",
        mental_model="Trace Activity Is Not Progress",
    )


def test_review_findings_fails_when_unit_uncovered() -> None:
    units = [_sample_unit("u1", "detrix-core"), _sample_unit("u2", "detrix-core")]
    findings = [_sample_finding("f1", ["u1"])]

    report = review_findings(units=units, findings=findings)

    assert report.passed is False
    assert report.uncovered_unit_ids == ["u2"]


def test_review_findings_rejects_missing_evidence() -> None:
    units = [_sample_unit("u1", "detrix-core")]
    findings = [_sample_finding("f1", ["u1"], evidence=[])]

    report = review_findings(units=units, findings=findings)

    assert report.passed is False
    assert report.rejected_finding_ids == ["f1"]


def test_review_findings_requires_resolution_for_partial() -> None:
    units = [_sample_unit("u1", "detrix-core")]
    findings = [_sample_finding("f1", ["u1"], distance_to_goal="partial")]

    report = review_findings(units=units, findings=findings)

    assert report.passed is False
    assert report.rejected_finding_ids == ["f1"]
