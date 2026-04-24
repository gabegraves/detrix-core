#!/usr/bin/env python3
"""Ingest an AXV2 RunArtifact into the Detrix bridge.

Usage:
    python scripts/ingest_axv2_run.py path/to/run_artifact.json
    python scripts/ingest_axv2_run.py --run-demo
    python scripts/ingest_axv2_run.py artifact.json --bridge-url http://localhost:7432
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib import error, request

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Ingest an AXV2 run artifact JSON into a running Detrix bridge."
        )
    )
    parser.add_argument(
        "artifact",
        nargs="?",
        type=Path,
        help="Path to the AXV2 run artifact JSON file.",
    )
    parser.add_argument(
        "--domain",
        default="xrd",
        help="Domain label stored on the resulting governed trajectories.",
    )
    parser.add_argument(
        "--bridge-url",
        default="http://localhost:7432",
        help="Detrix bridge base URL.",
    )
    parser.add_argument(
        "--run-demo",
        action="store_true",
        help="Run AXV2 'make demo' first, then ingest the latest resulting artifact.",
    )
    parser.add_argument(
        "--axv2-dir",
        type=Path,
        default=Path.home() / "Desktop" / "AgentXRD_v2",
        help="Path to the AgentXRD_v2 repo used with --run-demo.",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Ingest directly into local SQLite stores instead of POSTing to the bridge.",
    )
    parser.add_argument(
        "--evidence-db",
        type=Path,
        default=Path(".detrix/evidence.db"),
        help="Local evidence SQLite path used with --local.",
    )
    parser.add_argument(
        "--audit-db",
        type=Path,
        default=Path(".detrix/audit.db"),
        help="Local audit SQLite path used with --local.",
    )
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Print the ingest result as JSON.",
    )
    return parser


def find_latest_artifact(search_dir: Path) -> Path | None:
    """Find the most recent run_artifact.json or likely artifact JSON."""
    candidates = list(search_dir.rglob("run_artifact.json"))
    if not candidates:
        candidates = [
            candidate
            for candidate in search_dir.rglob("*.json")
            if "run" in candidate.stem or "artifact" in candidate.stem
        ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _resolve_artifact_path(args: argparse.Namespace) -> Path:
    if args.run_demo:
        axv2_dir = args.axv2_dir
        if not axv2_dir.exists():
            raise ValueError(f"AXV2 not found at {axv2_dir}")
        print(f"Running AXV2 demo in {axv2_dir}...")
        result = subprocess.run(
            ["make", "demo"],
            cwd=axv2_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise ValueError(f"Demo failed:\n{result.stderr}")
        print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)

        artifact_path = find_latest_artifact(axv2_dir / "outputs")
        if artifact_path is None:
            artifact_path = find_latest_artifact(axv2_dir / "reports")
        if artifact_path is None:
            raise ValueError("No RunArtifact found after demo run")
        print(f"Found artifact: {artifact_path}")
        return artifact_path

    if args.artifact is None:
        raise ValueError("Provide an artifact path or use --run-demo")
    return args.artifact


def _load_artifact(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Artifact not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Artifact is not valid JSON: {path}") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"Artifact must decode to a JSON object: {path}")

    required_fields = {
        "run_id",
        "timestamp",
        "pipeline_version",
        "steps",
        "success",
        "total_duration_ms",
        "model_versions",
        "gate_history",
        "terminal_routes",
    }
    missing = sorted(field for field in required_fields if field not in payload)
    if missing:
        raise ValueError(
            f"Artifact is missing required fields: {', '.join(missing)}"
        )
    return payload


def _ingest_local(
    *,
    artifact: dict[str, Any],
    domain: str,
    evidence_db: Path,
    audit_db: Path,
) -> dict[str, Any]:
    from detrix.adapters.axv2 import project_to_audit_log, run_artifact_to_trajectories
    from detrix.runtime.audit import AuditLog
    from detrix.runtime.trajectory_store import TrajectoryStore

    run_id = str(artifact.get("run_id", ""))
    audit = AuditLog(str(audit_db))
    if run_id and audit.get_run(run_id) is not None:
        raise ValueError(f"Duplicate run_id: {run_id}")

    trajectories = run_artifact_to_trajectories(artifact, domain=domain)
    store = TrajectoryStore(str(evidence_db))

    try:
        project_to_audit_log(artifact, audit)
        for trajectory in trajectories:
            store.append(trajectory)
    except sqlite3.IntegrityError as exc:
        raise ValueError(f"Duplicate run_id or trajectory_id: {run_id}") from exc

    return {
        "mode": "local",
        "run_id": run_id,
        "domain": domain,
        "count": len(trajectories),
        "trajectory_ids": [trajectory.trajectory_id for trajectory in trajectories],
        "audit_db": str(audit_db),
        "evidence_db": str(evidence_db),
    }


def _bridge_endpoint(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/ingest"


def _ingest_remote(
    *,
    artifact: dict[str, Any],
    domain: str,
    bridge_url: str,
) -> dict[str, Any]:
    payload = json.dumps({"run_artifact": artifact, "domain": domain}).encode("utf-8")
    req = request.Request(
        _bridge_endpoint(bridge_url),
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=30.0) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        if exc.code == 409:
            body = exc.read().decode("utf-8", errors="replace")
            try:
                response_data = json.loads(body)
            except json.JSONDecodeError:
                response_data = {"detail": body}
            print(f"Already ingested: {artifact.get('run_id', 'unknown')}")
            return {
                "mode": "remote",
                "run_id": str(artifact.get("run_id", "")),
                "domain": domain,
                "count": 0,
                "trajectory_ids": [],
                "bridge_url": bridge_url.rstrip("/"),
                "detail": response_data.get("detail", response_data),
            }
        detail = exc.read().decode("utf-8", errors="replace")
        raise ValueError(
            f"Bridge ingest failed with HTTP {exc.code}: {detail}"
        ) from exc
    except error.URLError as exc:
        raise ValueError(f"Bridge ingest failed: {exc.reason}") from exc

    response_data["mode"] = "remote"
    response_data["run_id"] = str(artifact.get("run_id", ""))
    response_data["domain"] = domain
    response_data["bridge_url"] = bridge_url.rstrip("/")
    return response_data


def _format_text_result(result: dict[str, Any]) -> str:
    trajectory_ids = ", ".join(result.get("trajectory_ids", [])) or "<none>"
    lines = [
        f"mode: {result['mode']}",
        f"run_id: {result['run_id']}",
        f"domain: {result['domain']}",
        f"count: {result['count']}",
        f"trajectory_ids: {trajectory_ids}",
    ]
    if result["mode"] == "remote":
        lines.append(f"bridge_url: {result['bridge_url']}")
    else:
        lines.append(f"audit_db: {result['audit_db']}")
        lines.append(f"evidence_db: {result['evidence_db']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        artifact_path = _resolve_artifact_path(args)
        artifact = _load_artifact(artifact_path)
        if args.local:
            result = _ingest_local(
                artifact=artifact,
                domain=args.domain,
                evidence_db=args.evidence_db,
                audit_db=args.audit_db,
            )
        else:
            print(f"Ingesting {artifact_path} -> {args.bridge_url.rstrip('/')}/ingest ...")
            result = _ingest_remote(
                artifact=artifact,
                domain=args.domain,
                bridge_url=args.bridge_url,
            )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.json_output:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(_format_text_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
