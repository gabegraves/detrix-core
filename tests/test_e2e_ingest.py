"""End-to-end bridge ingest to trajectory store to training export."""

from __future__ import annotations

import importlib
import json
import os
import tempfile

import pytest

pytest.importorskip("fastapi")

from starlette.testclient import TestClient

from detrix.improvement.exporter import TrainingExporter
from detrix.runtime.trajectory_store import TrajectoryStore


class TestEndToEndIngestExport:
    def _ingest_and_export(self, tmp_dir: str) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
        os.environ["DETRIX_EVIDENCE_DB"] = os.path.join(tmp_dir, "evidence.db")
        os.environ["DETRIX_AUDIT_DB"] = os.path.join(tmp_dir, "audit.db")

        import detrix.bridge.app as bridge_mod

        importlib.reload(bridge_mod)
        client = TestClient(bridge_mod.app)

        artifact: dict[str, object] = {
            "run_id": "e2e-test",
            "timestamp": "2026-04-24T12:00:00",
            "pipeline_version": "test",
            "config_hash": "ch",
            "input_file_hash": "ih",
            "steps": [
                {"name": "SCORING", "status": "success", "duration_ms": 100},
                {"name": "REFINEMENT", "status": "success", "duration_ms": 200},
            ],
            "success": True,
            "total_duration_ms": 300,
            "model_versions": {},
            "gate_history": [
                {
                    "sample_id": "s1",
                    "gate_name": "post_score_quality_gate",
                    "status": "passed",
                    "decision": "continue",
                    "evidence": {"confidence": 0.92},
                },
                {
                    "sample_id": "s1",
                    "gate_name": "post_refinement_quality_gate",
                    "status": "passed",
                    "decision": "continue",
                    "evidence": {"rwp": 8.5, "gof": 1.8},
                },
            ],
            "terminal_routes": {},
        }
        resp = client.post("/ingest", json={"run_artifact": artifact, "domain": "xrd"})
        assert resp.status_code == 200

        store = TrajectoryStore(os.path.join(tmp_dir, "evidence.db"))
        exporter = TrainingExporter(store)

        sft_path = exporter.export_sft(os.path.join(tmp_dir, "sft.jsonl"), domain="xrd")
        grpo_path = exporter.export_grpo(os.path.join(tmp_dir, "grpo.jsonl"), domain="xrd")

        sft_rows = [json.loads(line) for line in open(sft_path, encoding="utf-8")]
        grpo_rows = [json.loads(line) for line in open(grpo_path, encoding="utf-8")]
        return sft_rows, grpo_rows

    def test_ingest_to_sft_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sft_rows, _ = self._ingest_and_export(tmp)
            assert len(sft_rows) == 1
            assert "prompt" in sft_rows[0]
            assert "completion" in sft_rows[0]

    def test_ingest_to_grpo_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _, grpo_rows = self._ingest_and_export(tmp)
            assert len(grpo_rows) == 1
            assert grpo_rows[0]["governance_score"] == 1.0
            assert len(grpo_rows[0]["gate_verdicts"]) == 2
            assert all(verdict == "accept" for verdict in grpo_rows[0]["gate_verdicts"])
