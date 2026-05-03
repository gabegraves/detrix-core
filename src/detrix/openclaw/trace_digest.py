"""Digest OpenClaw JSONL traces into governed trajectories."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from detrix.core.admission import AdmissionBuilder
from detrix.core.governance import Decision, GateContext, VerdictContract
from detrix.core.trajectory import GovernedTrajectory
from detrix.openclaw.gates import OpenClawGovernanceGate
from detrix.runtime.trajectory_store import TrajectoryStore


@dataclass(frozen=True)
class DigestSummary:
    """Summary of OpenClaw trace digestion."""

    total: int
    stored: int
    skipped: int
    decisions: dict[str, int] = field(default_factory=dict)
    failure_patterns: dict[str, int] = field(default_factory=dict)
    trajectories: list[GovernedTrajectory] = field(default_factory=list)


def digest_openclaw_traces(
    trace_path: str | Path,
    *,
    store: TrajectoryStore | None = None,
    config: dict[str, Any] | None = None,
    limit: int | None = None,
) -> DigestSummary:
    """Read OpenClaw JSONL traces, run gates, and optionally append trajectories."""
    path = Path(trace_path)
    gate = OpenClawGovernanceGate()
    trajectories: list[GovernedTrajectory] = []
    decisions: Counter[str] = Counter()
    failures: Counter[str] = Counter()
    total = 0
    skipped = 0

    for source_path in _jsonl_paths(path):
        with source_path.open(encoding="utf-8") as file:
            for line_index, line in enumerate(file):
                if limit is not None and total >= limit:
                    break
                raw = line.strip()
                if not raw:
                    continue
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    skipped += 1
                    continue
                extracted = extract_openclaw_trace(payload, source_path=source_path, line_index=line_index)
                if extracted["completion"] == "":
                    skipped += 1
                    continue
                context = GateContext(
                    run_id=extracted["run_id"],
                    step_index=line_index,
                    prior_verdicts=[],
                    config=config or {},
                )
                verdict = gate.evaluate(
                    {
                        "message": extracted["completion"],
                        "agent_output": extracted["completion"],
                        "prompt": extracted["prompt"],
                        "delivery_metadata": extracted["delivery_metadata"],
                    },
                    context,
                )
                trajectory = build_trajectory(extracted, [verdict], gate)
                trajectory = AdmissionBuilder.compute_admission(trajectory)
                trajectories.append(trajectory)
                decisions[verdict.decision.value] += 1
                failures.update(verdict.reason_codes)
                if store is not None:
                    try:
                        store.append(trajectory)
                    except sqlite3.IntegrityError:
                        skipped += 1
                    else:
                        total += 1
                        continue
                total += 1
        if limit is not None and total >= limit:
            break

    return DigestSummary(
        total=total,
        stored=len(trajectories) if store is not None else 0,
        skipped=skipped,
        decisions=dict(decisions),
        failure_patterns=dict(failures),
        trajectories=trajectories,
    )


def extract_openclaw_trace(
    payload: dict[str, Any],
    *,
    source_path: Path,
    line_index: int,
) -> dict[str, Any]:
    """Extract a prompt/completion pair from common OpenClaw session/cron shapes."""
    session_id = str(
        payload.get("session_id")
        or payload.get("run_id")
        or payload.get("conversation_id")
        or source_path.stem
    )
    timestamp = _first_value(payload, ("timestamp", "created_at", "finished_at", "time"))
    prompt = _first_value(
        payload,
        ("user_input", "prompt", "input", "question", "request", "task"),
    )
    completion = _first_value(
        payload,
        ("agent_output", "completion", "output", "response", "message", "text", "summary"),
    )
    if completion == "" and isinstance(payload.get("messages"), list):
        prompt, completion = _extract_from_messages(payload["messages"])
    return {
        "trajectory_id": f"{session_id}-{source_path.stem}-{line_index}",
        "run_id": session_id,
        "timestamp": _parse_datetime(timestamp),
        "prompt": str(prompt),
        "completion": str(completion),
        "delivery_metadata": payload.get("delivery_metadata") or payload.get("telegram") or {},
        "raw": payload,
    }


def build_trajectory(
    extracted: dict[str, Any],
    verdicts: list[VerdictContract],
    gate: OpenClawGovernanceGate,
) -> GovernedTrajectory:
    verdict_dicts = [verdict.to_dict() for verdict in verdicts]
    accept_count = sum(1 for verdict in verdicts if verdict.decision == Decision.ACCEPT)
    gate_pass_rate = accept_count / len(verdicts) if verdicts else 0.0
    rejection_type = next(
        (verdict.rejection_type for verdict in verdicts if verdict.rejection_type),
        None,
    )
    return GovernedTrajectory(
        trajectory_id=extracted["trajectory_id"],
        run_id=extracted["run_id"],
        domain="openclaw",
        prompt=extracted["prompt"],
        completion=extracted["completion"],
        verdicts=verdict_dicts,
        governance_score=gate_pass_rate,
        gate_pass_rate=gate_pass_rate,
        rejection_type=rejection_type,
        evaluator_versions={gate.gate_id: gate.version},
        gate_versions={gate.gate_id: gate.version},
        started_at=extracted["timestamp"],
        finished_at=extracted["timestamp"],
    )


def _jsonl_paths(path: Path) -> list[Path]:
    if path.is_dir():
        return sorted(path.glob("*.jsonl"))
    return [path]


def _first_value(payload: Any, keys: tuple[str, ...]) -> str:
    if not isinstance(payload, dict):
        return ""
    for key in keys:
        value = payload.get(key)
        if value is not None:
            if isinstance(value, str):
                return value
            return json.dumps(value, sort_keys=True)
    for value in payload.values():
        if isinstance(value, dict):
            found = _first_value(value, keys)
            if found:
                return found
    return ""


def _extract_from_messages(messages: list[Any]) -> tuple[str, str]:
    prompt = ""
    completion = ""
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role", "")).lower()
        content = str(message.get("content") or message.get("text") or "")
        if role in {"user", "human"}:
            prompt = content
        elif role in {"assistant", "agent", "system"}:
            completion = content
    return prompt, completion


def _parse_datetime(raw: str) -> datetime:
    if raw:
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)
