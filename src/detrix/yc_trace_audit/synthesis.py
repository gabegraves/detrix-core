"""Render the YC process playbook from reviewed findings."""

from __future__ import annotations

from collections import defaultdict

from detrix.yc_trace_audit.projects import AUDIT_WINDOW, CORE_PROJECTS
from detrix.yc_trace_audit.schema import AgentFinding, AuditUnit, ReviewReport


def render_playbook(
    *,
    units: list[AuditUnit],
    findings: list[AgentFinding],
    review_report: ReviewReport,
) -> str:
    if not review_report.passed:
        return (
            "# YC Process Playbook - SYNTHESIS BLOCKED\n\n"
            f"Uncovered units: {', '.join(review_report.uncovered_unit_ids) or 'none'}\n\n"
            f"Rejected findings: {', '.join(review_report.rejected_finding_ids) or 'none'}\n"
        )
    accepted = [f for f in findings if f.finding_id in set(review_report.accepted_finding_ids)]
    by_distance: dict[str, list[AgentFinding]] = defaultdict(list)
    for finding in accepted:
        by_distance[finding.distance_to_goal].append(finding)
    unit_by_id = {unit.unit_id: unit for unit in units}
    lines = [
        "# YC Process Playbook - 2026-05-05",
        "",
        f"Audit window: `{AUDIT_WINDOW.start_iso}` through `{AUDIT_WINDOW.end_iso}`.",
        f"Reviewer coverage: {review_report.covered_units}/{review_report.total_units} units; rejected findings: {len(review_report.rejected_finding_ids)}.",
        "",
        "## What Works",
        *_finding_bullets(by_distance.get("closed", []), fallback="- No fully closed units were found by accepted findings."),
        "",
        "## What Fails",
        *_finding_bullets(by_distance.get("zero", []) + by_distance.get("wide", []), fallback="- No zero/wide failures were accepted by the reviewer."),
        "",
        "## Distance to Goals",
    ]
    for project_id, project in CORE_PROJECTS.items():
        project_findings = [finding for finding in accepted if finding.project_id == project_id]
        lines.extend([
            f"### {project.display_name}",
            f"Goal docs: {', '.join(str(path) for path in project.goal_docs)}",
        ])
        lines.extend(_finding_bullets(project_findings, fallback="- No accepted findings for this project."))
        lines.append("")
    lines.extend(
        [
            "## Product Direction",
            "- Demo Detrix as governed admission for high-stakes agent state transitions, not as a generic trace viewer. Use closed and partial units only when they show durable artifacts, bead/commit closure, deterministic gates, or explicit accept/reject/request-more-data routes.",
            "- Keep AgentXRD support-only evidence diagnostic; do not promote support-only rescue paths as ACCEPT evidence.",
            "- Treat ParabolaHunter process wins as insufficient for trading proof unless real-priced, route-aware replay is cited.",
            "",
            "## Recommended Demo Sprint Process",
            "- Start every sprint with a named workflow, owner, success metric, evidence inputs, and stop condition.",
            "- Convert each run into an intent -> outcome -> distance-to-goal unit before writing narrative updates.",
            "- Require deterministic reviewer coverage before YC/customer synthesis; rejected findings become next actions, not marketing claims.",
            "- Prefer demos that end in governed admission labels: ACCEPT, reject/exclude, REQUEST_MORE_DATA, training eligibility, or promotion after replay.",
            "",
            "## Evidence Appendix",
        ]
    )
    for finding in accepted:
        cited_units = ", ".join(finding.unit_ids)
        citations = ", ".join(finding.evidence)
        lines.append(f"- `{finding.finding_id}` ({finding.role}, {finding.distance_to_goal}) units={cited_units}; evidence={citations}")
        for unit_id in finding.unit_ids:
            unit = unit_by_id.get(unit_id)
            if unit:
                lines.append(f"  - unit `{unit.unit_id}` sources={', '.join(unit.source_ids)} goal_docs={', '.join(str(path) for path in unit.goal_doc_paths)}")
    lines.append("")
    return "\n".join(lines)


def _finding_bullets(findings: list[AgentFinding], *, fallback: str) -> list[str]:
    if not findings:
        return [fallback]
    return [f"- `{finding.finding_id}` [{finding.project_id or 'cross-project'}]: {finding.claim}" for finding in findings]
