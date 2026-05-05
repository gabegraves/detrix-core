"""Deterministic reviewer for YC trace audit findings."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from detrix.yc_trace_audit.packets import ALL_ROLES, SPECIALIST_ROLES
from detrix.yc_trace_audit.projects import CORE_PROJECTS
from detrix.yc_trace_audit.schema import AgentFinding, AuditUnit, ReviewReport

EVIDENCE_PREFIXES = ("unit:", "trace:", "session:", "git:", "plan:", "bead:")
NEEDS_RESOLUTION = {"partial", "wide", "zero"}


def load_findings(path: Path) -> list[AgentFinding]:
    findings: list[AgentFinding] = []
    if not path.exists():
        return findings
    files = sorted(path.glob("*.jsonl")) if path.is_dir() else [path]
    for file_path in files:
        with file_path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    findings.append(AgentFinding.model_validate_json(line))
                except (ValidationError, ValueError):
                    continue
    return findings


def review_findings(units: list[AuditUnit], findings: list[AgentFinding]) -> ReviewReport:
    unit_ids = {unit.unit_id for unit in units}
    accepted: list[str] = []
    rejected: list[str] = []
    covered: set[str] = set()
    for finding in findings:
        if _reject_reason(finding, unit_ids) is not None:
            rejected.append(finding.finding_id)
            continue
        accepted.append(finding.finding_id)
        covered.update(finding.unit_ids)
    uncovered = sorted(unit_ids - covered)
    return ReviewReport(
        passed=not uncovered and not rejected,
        total_units=len(unit_ids),
        covered_units=len(covered),
        uncovered_unit_ids=uncovered,
        rejected_finding_ids=sorted(rejected),
        accepted_finding_ids=sorted(accepted),
    )


def write_review_report(units: list[AuditUnit], findings: list[AgentFinding], output_path: Path) -> ReviewReport:
    report = review_findings(units, findings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return report


def _reject_reason(finding: AgentFinding, unit_ids: set[str]) -> str | None:
    if finding.role not in ALL_ROLES:
        return "unsupported role"
    if finding.project_id is not None and finding.project_id not in CORE_PROJECTS:
        return "unknown project"
    if not finding.unit_ids or any(unit_id not in unit_ids for unit_id in finding.unit_ids):
        return "unknown unit"
    if not any(evidence.startswith(EVIDENCE_PREFIXES) for evidence in finding.evidence):
        return "missing cited evidence"
    if finding.role in SPECIALIST_ROLES and not finding.mental_model:
        return "missing mental model"
    if finding.role in SPECIALIST_ROLES and finding.distance_to_goal in NEEDS_RESOLUTION:
        claim = finding.claim.lower()
        if "next action" not in claim and "resolution path" not in claim:
            return "missing resolution path"
    return None


def findings_to_jsonl(findings: list[AgentFinding], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for finding in findings:
            handle.write(json.dumps(finding.model_dump(mode="json"), sort_keys=True) + "\n")
