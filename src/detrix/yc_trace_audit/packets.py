"""Agent packet writer for the YC trace audit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from detrix.yc_trace_audit.projects import AUDIT_WINDOW
from detrix.yc_trace_audit.schema import AgentPacket, AgentRole, AuditUnit

SPECIALIST_ROLES: tuple[AgentRole, ...] = (
    "success_patterns",
    "friction_iteration",
    "failure_modes",
    "compounding_decisions",
    "external_research",
)
ALL_ROLES: tuple[AgentRole, ...] = (*SPECIALIST_ROLES, "reviewer")

MENTAL_MODEL_TRANSFER = """### Model 1: Trace Activity Is Not Progress
Failure mode example:
- A Detrix or Mission Control session produces many Langfuse traces, suggestions, or dashboard rows, but no governed state transition lands: no accepted gate, no replay proof, no closed bead, no durable commit, no final artifact.
Why shallow audits get it wrong:
- They treat trace volume or collector execution as evidence that the system improved.
Resolution path:
- Check whether the outcome became durable project state: commit still in HEAD, bead closed, playbook/doc emitted, artifact consumed by a downstream gate, or verified command output.
- If traces exist but no durable transition happened, classify as `partial` or `zero` distance closure depending on whether the trace still produced a reusable diagnostic.
- Evidence should cite both the trace/session id and the missing or present durable artifact.

### Model 2: Planning Artifacts Are Not Implementation
Failure mode example:
- A session creates a plan for AgentXRD, ParabolaHunter, or Detrix and marks the direction as promising, but the target repo has no source change, no test, no run artifact, and no bead closure.
Why shallow audits get it wrong:
- They collapse "the plan exists" into "the capability exists."
Resolution path:
- Separate upstream intent from downstream execution. Link the planning session to any child execution sessions before judging.
- If no child session or landed artifact exists, classify the unit as planning-only and measure it against planning goals, not implementation goals.
- If a later child session implemented it, judge the linked unit by the child outcome and cite both parent plan and child artifact.

### Model 3: Support-Only Evidence Cannot Become Promotion Evidence
Failure mode example:
- An AgentXRD trace finds a useful support-only CIF, fallback, or rescue path, and the session narrative sounds successful, but the candidate is `accept_eligible=false`, has support-only provenance, or lacks row-level truth/calibration evidence.
Why shallow audits get it wrong:
- They count a plausible match or candidate found as scientific success.
Resolution path:
- Inspect whether the artifact is benchmark-eligible, support-only, or diagnostic-only.
- Treat support-only evidence as useful process learning, not as an ACCEPT, promotion, or benchmark-ready result.
- Cite candidate-level provenance, route verdict, and any explicit `support_only` / `accept_eligible` fields.

### Model 4: Real-Priced Replay Beats Alert Narrative
Failure mode example:
- A ParabolaHunter session improves alert text, social signal summaries, or a decision packet shape, but the replay is not real-priced, route-aware, or wired through the Sniper/Scalper/Sentinel path it claims to improve.
Why shallow audits get it wrong:
- They reward cleaner explanations or plausible strategy narratives without checking trading-path evidence.
Resolution path:
- Check replay inputs, pricing provenance, route ownership, and whether the changed path is actually exercised.
- If the trace only improved narrative hygiene, classify as process quality, not trading edge.
- Evidence should cite replay command/artifact, pricing source, and agent route.

### Model 5: Admission Boundary Is the Detrix Product Signal
Failure mode example:
- A Detrix session frames the result as "we can observe traces" or "we can fine-tune from traces" but does not show a governed admission decision: accept, reject, request more data, exclude from training, label as DPO negative, or promote after replay.
Why shallow audits get it wrong:
- They compare Detrix to generic observability or training tools and miss the actual product boundary.
Resolution path:
- Look for explicit state-transition handling: what was proposed, what policy/gate evaluated it, what route resulted, and what durable next action followed.
- If the session only improves observability, classify it as substrate progress, not product proof.
- Evidence should cite admission labels, gate records, training eligibility, replay status, or blocked transition rationale.
"""

BASE_PROMPT = """Core question: for each assigned unit, what was the intent going in, what outcome happened, and how close did that outcome get to the goals in the project's AGENTS.md / CLAUDE.md?

Return JSONL findings only. Every finding must include: finding_id, role, unit_ids, project_id, claim, evidence, distance_to_goal, confidence, mental_model.
Evidence must cite unit ids plus trace/session/git/plan/bead ids from the packet. Do not introduce uncited claims.

Use the mental models in this packet. For every non-trivial finding, name the closest failure mode or success model and explain the resolution path in one sentence.
Use this exact reasoning frame: intent -> outcome -> distance to goal.
"""

ROLE_PROMPTS: dict[AgentRole, str] = {
    "success_patterns": "Find units where intent matched outcome and moved toward project goals.",
    "friction_iteration": "Find units where work looped, stalled, diverged, or required major iteration.",
    "failure_modes": "Find units with zero durable progress toward project goals.",
    "compounding_decisions": "Find decisions that were reused across later units or projects.",
    "external_research": "Read existing detrix-core docs first, then add current external sources only for process-audit, agent governance, and YC demo/product direction framing.",
    "reviewer": "Compare findings against coverage_manifest.json; reject uncited findings and list uncovered units.",
}


def write_agent_packets(units: list[AuditUnit], output_dir: Path, manifest_path: Path | None = None) -> list[AgentPacket]:
    output_dir.mkdir(parents=True, exist_ok=True)
    resolved_manifest = manifest_path or output_dir / "coverage_manifest.json"
    unit_manifest = [_unit_payload(unit) for unit in units]
    project_ids = sorted({unit.project_id for unit in units})
    packets: list[AgentPacket] = []
    for role in ALL_ROLES:
        prompt = _prompt_for(role)
        packet = AgentPacket(
            role=role,
            audit_window=AUDIT_WINDOW,
            project_ids=project_ids,
            unit_ids=[unit.unit_id for unit in units],
            prompt=prompt,
            manifest_path=resolved_manifest,
        )
        payload: dict[str, Any] = packet.model_dump(mode="json")
        payload["units"] = unit_manifest
        payload["role_instruction"] = ROLE_PROMPTS[role]
        if role == "reviewer":
            payload["reviewer_checklist"] = [
                "Every source record is in the Feb 1-May 5 window.",
                "Cron rows are excluded with an explicit exclusion count.",
                "Every unit is assigned to exactly one core project.",
                "Every unit has AGENTS.md/CLAUDE.md goal-doc references.",
                "Every accepted finding cites at least one unit id and one evidence id.",
                "Synthesis is blocked unless reviewer passes.",
            ]
        else:
            payload["mental_models_for_expert_transfer"] = MENTAL_MODEL_TRANSFER
        (output_dir / f"{role}.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        packets.append(packet)
    return packets


def _prompt_for(role: AgentRole) -> str:
    if role == "reviewer":
        return f"{BASE_PROMPT}\nReviewer checklist: validate coverage, citations, mental_model use, and resolution paths."
    return f"{BASE_PROMPT}\nRole focus: {ROLE_PROMPTS[role]}\n\n{MENTAL_MODEL_TRANSFER}"


def _unit_payload(unit: AuditUnit) -> dict[str, Any]:
    payload = unit.model_dump(mode="json")
    evidence_ids: list[str] = [f"unit:{unit.unit_id}"]
    evidence_ids.extend(f"source:{source_id}" for source_id in unit.source_ids)
    for session_id in unit.correlation_ids.get("sessions", []):
        evidence_ids.append(f"session:{session_id}")
    for trace_id in unit.correlation_ids.get("traces", []):
        evidence_ids.append(f"trace:{trace_id}")
    for git_id in unit.correlation_ids.get("git", []):
        evidence_ids.append(f"git:{git_id}")
    for plan_id in unit.correlation_ids.get("plans", []):
        evidence_ids.append(f"plan:{plan_id}")
    for bead_id in unit.correlation_ids.get("beads", []):
        evidence_ids.append(f"bead:{bead_id}")
    payload["evidence_ids"] = evidence_ids
    return payload
