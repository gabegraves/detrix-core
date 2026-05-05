"""Runbook orchestration for the YC trace audit harness."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from detrix.yc_trace_audit.correlator import attach_correlations
from detrix.yc_trace_audit.linker import build_audit_units
from detrix.yc_trace_audit.packets import write_agent_packets
from detrix.yc_trace_audit.projects import AUDIT_WINDOW
from detrix.yc_trace_audit.reviewer import load_findings, write_review_report
from detrix.yc_trace_audit.schema import AuditUnit, ReviewReport, SourceRecord
from detrix.yc_trace_audit.session_sources import (
    DEFAULT_SESSION_ROOTS,
    MISSION_CONTROL_DB,
    load_all_sources,
)
from detrix.yc_trace_audit.synthesis import render_playbook

DEFAULT_OUTPUT_DIR = Path("outputs/yc_trace_audit_20260505")
DEFAULT_PLAYBOOK_PATH = Path("docs/yc-process-playbook-2026-05-05.md")


def extract_sources_and_units(
    *,
    mission_control_db: Path = MISSION_CONTROL_DB,
    session_roots: list[Path] | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    roots = DEFAULT_SESSION_ROOTS if session_roots is None else session_roots
    raw_sources = load_all_sources(db_path=mission_control_db, session_roots=roots)
    units = attach_correlations(build_audit_units(raw_sources))
    raw_path = output_dir / "raw_sources.jsonl"
    units_path = output_dir / "session_units.jsonl"
    manifest_path = output_dir / "coverage_manifest.json"
    _write_jsonl(raw_path, raw_sources)
    _write_jsonl(units_path, units)
    manifest = _coverage_manifest(raw_sources, units, mission_control_db, roots)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"raw_sources": raw_path, "session_units": units_path, "coverage_manifest": manifest_path}


def write_packets_from_manifest(*, output_dir: Path = DEFAULT_OUTPUT_DIR) -> list[Path]:
    units = _read_jsonl_models(output_dir / "session_units.jsonl", AuditUnit)
    packet_dir = output_dir / "agent_packets"
    packets = write_agent_packets(units=units, output_dir=packet_dir, manifest_path=output_dir / "coverage_manifest.json")
    return [packet_dir / f"{packet.role}.json" for packet in packets]


def review_agent_findings(*, output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    units = _read_jsonl_models(output_dir / "session_units.jsonl", AuditUnit)
    findings = load_findings(output_dir / "agent_findings")
    write_review_report(units, findings, output_dir / "review_report.json")
    return output_dir / "review_report.json"


def synthesize_playbook(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    playbook_path: Path = DEFAULT_PLAYBOOK_PATH,
) -> Path:
    units = _read_jsonl_models(output_dir / "session_units.jsonl", AuditUnit)
    findings = load_findings(output_dir / "agent_findings")
    report = ReviewReport.model_validate_json((output_dir / "review_report.json").read_text(encoding="utf-8"))
    markdown = render_playbook(units=units, findings=findings, review_report=report)
    playbook_path.parent.mkdir(parents=True, exist_ok=True)
    playbook_path.write_text(markdown, encoding="utf-8")
    return playbook_path


def _coverage_manifest(
    sources: list[SourceRecord],
    units: list[AuditUnit],
    mission_control_db: Path,
    session_roots: list[Path],
) -> dict[str, Any]:
    return {
        "audit_window": AUDIT_WINDOW.model_dump(mode="json"),
        "mission_control_db": str(mission_control_db),
        "session_roots": [str(root) for root in session_roots],
        "source_count": len(sources),
        "unit_count": len(units),
        "cron_excluded_count": 0,
        "source_counts_by_project": dict(Counter(source.project_id for source in sources)),
        "unit_counts_by_project": dict(Counter(unit.project_id for unit in units)),
        "unit_ids": [unit.unit_id for unit in units],
    }


def _write_jsonl(path: Path, rows: list[Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            if hasattr(row, "model_dump"):
                payload = row.model_dump(mode="json")
            else:
                payload = row
            handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _read_jsonl_models(path: Path, model: type[Any]) -> list[Any]:
    rows: list[Any] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(model.model_validate_json(line))
    return rows
