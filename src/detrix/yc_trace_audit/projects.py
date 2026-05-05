"""Static project registry for the YC trace audit."""

from __future__ import annotations

from pathlib import Path

from detrix.yc_trace_audit.schema import AuditWindow, ProjectDefinition

AUDIT_WINDOW = AuditWindow(
    start_iso="2026-02-01T00:00:00-05:00",
    end_iso="2026-05-05T23:59:59-04:00",
)

CORE_PROJECTS: dict[str, ProjectDefinition] = {
    "detrix-core": ProjectDefinition(
        project_id="detrix-core",
        display_name="Detrix Core",
        root=Path("/home/gabriel/Desktop/detrix-core"),
        aliases=["detrix", "Detrix", "detrix-core", "Desktop/detrix-core"],
        goal_docs=[
            Path("/home/gabriel/Desktop/detrix-core/AGENTS.md"),
            Path("/home/gabriel/Desktop/detrix-core/CLAUDE.md"),
        ],
    ),
    "agentxrd-v2": ProjectDefinition(
        project_id="agentxrd-v2",
        display_name="AgentXRD v2",
        root=Path("/home/gabriel/Desktop/AgentXRD_v2"),
        aliases=["AgentXRD", "AgentXRD_v2", "mc-agentxrd_v2"],
        goal_docs=[
            Path("/home/gabriel/Desktop/AgentXRD_v2/AGENTS.md"),
            Path("/home/gabriel/Desktop/AgentXRD_v2/CLAUDE.md"),
        ],
    ),
    "parabolahunter": ProjectDefinition(
        project_id="parabolahunter",
        display_name="ParabolaHunter",
        root=Path("/home/gabriel/Desktop/ParabolaHunter"),
        aliases=["ParabolaHunter", "ParaboloHunter", "PH"],
        goal_docs=[
            Path("/home/gabriel/Desktop/ParabolaHunter/AGENTS.md"),
            Path("/home/gabriel/Desktop/ParabolaHunter/CLAUDE.md"),
        ],
    ),
    "mission-control": ProjectDefinition(
        project_id="mission-control",
        display_name="Mission Control",
        root=Path("/home/gabriel/mission-control"),
        aliases=["mission-control", "Mission Control", "mc"],
        goal_docs=[
            Path("/home/gabriel/mission-control/AGENTS.md"),
            Path("/home/gabriel/mission-control/CLAUDE.md"),
        ],
    ),
}


def project_for_path(path: Path) -> ProjectDefinition:
    resolved = path.expanduser()
    for project in CORE_PROJECTS.values():
        if resolved == project.root or project.root in resolved.parents:
            return project
    raise ValueError(f"path is outside core audit projects: {path}")


def project_for_text(text: str | None) -> ProjectDefinition | None:
    if not text:
        return None
    lowered = text.lower()
    for project in CORE_PROJECTS.values():
        if str(project.root).lower() in lowered:
            return project
        if any(alias.lower() in lowered for alias in project.aliases):
            return project
    return None
