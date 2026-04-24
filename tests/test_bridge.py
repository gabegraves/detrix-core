from __future__ import annotations

import importlib
import os
import sqlite3
import tempfile

import pytest

pytest.importorskip("fastapi")

from starlette.testclient import TestClient


class TestBridgeEndpoints:
    def _make_client(self, tmp_dir: str) -> TestClient:
        os.environ["DETRIX_EVIDENCE_DB"] = os.path.join(tmp_dir, "evidence.db")
        os.environ["DETRIX_AUDIT_DB"] = os.path.join(tmp_dir, "audit.db")

        import detrix.bridge.app as bridge_mod

        importlib.reload(bridge_mod)
        return TestClient(bridge_mod.app)

    def test_health(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = self._make_client(tmp)
            response = client.get("/health")
            assert response.status_code == 200
            assert response.json()["status"] == "ok"

    def test_ingest_writes_to_evidence_db(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = self._make_client(tmp)
            artifact = _make_artifact(
                gate_history=[
                    {
                        "sample_id": "s1",
                        "gate_name": "g1",
                        "status": "passed",
                        "decision": "continue",
                        "evidence": {"score": 0.9},
                    }
                ],
            )
            response = client.post("/ingest", json={"run_artifact": artifact, "domain": "xrd"})
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 1
            assert len(data["trajectory_ids"]) == 1

            evidence_path = os.path.join(tmp, "evidence.db")
            with sqlite3.connect(evidence_path) as conn:
                count = conn.execute("SELECT COUNT(*) FROM governed_trajectories").fetchone()
            assert count is not None
            assert count[0] == 1

    def test_ingest_writes_to_audit_db(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = self._make_client(tmp)
            artifact = _make_artifact(
                gate_history=[
                    {
                        "sample_id": "s1",
                        "gate_name": "score_gate",
                        "status": "passed",
                        "decision": "continue",
                        "evidence": {"confidence": 0.9},
                    }
                ],
            )
            response = client.post("/ingest", json={"run_artifact": artifact, "domain": "xrd"})
            assert response.status_code == 200

            audit_path = os.path.join(tmp, "audit.db")
            assert os.path.exists(audit_path)
            conn = sqlite3.connect(audit_path)
            conn.row_factory = sqlite3.Row
            run = conn.execute(
                "SELECT * FROM workflow_runs WHERE run_id = ?",
                ("run-test",),
            ).fetchone()
            assert run is not None
            assert run["workflow_name"] == "axv2-import"

            steps = conn.execute(
                "SELECT * FROM step_executions WHERE run_id = ?",
                ("run-test",),
            ).fetchall()
            assert len(steps) >= 1
            gated = [step for step in steps if step["gate_decision"] is not None]
            assert len(gated) >= 1
            assert gated[0]["gate_decision"] == "accept"
            assert gated[0]["gate_id"] == "score_gate"
            conn.close()

    def test_ingest_multi_sample(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = self._make_client(tmp)
            artifact = _make_artifact(
                run_id="run-multi",
                gate_history=[
                    {
                        "sample_id": "s1",
                        "gate_name": "g1",
                        "status": "passed",
                        "decision": "continue",
                    },
                    {
                        "sample_id": "s2",
                        "gate_name": "g1",
                        "status": "passed",
                        "decision": "continue",
                    },
                ],
            )
            response = client.post("/ingest", json={"run_artifact": artifact})
            assert response.status_code == 200
            assert response.json()["count"] == 2

    def test_ingest_empty_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = self._make_client(tmp)
            artifact = _make_artifact(run_id="run-empty")
            response = client.post("/ingest", json={"run_artifact": artifact})
            assert response.status_code == 200
            assert response.json()["count"] == 1

    def test_duplicate_run_id_returns_409(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = self._make_client(tmp)
            artifact = _make_artifact(
                run_id="run-dup",
                gate_history=[
                    {
                        "sample_id": "s1",
                        "gate_name": "g1",
                        "status": "passed",
                        "decision": "continue",
                    },
                ],
            )
            response_1 = client.post("/ingest", json={"run_artifact": artifact})
            assert response_1.status_code == 200

            response_2 = client.post("/ingest", json={"run_artifact": artifact})
            assert response_2.status_code == 409
            assert "duplicate" in response_2.json()["detail"].lower()


def _make_artifact(
    run_id: str = "run-test",
    gate_history: list[dict[str, object]] | None = None,
    terminal_routes: dict[str, dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "run_id": run_id,
        "timestamp": "2026-04-24T12:00:00",
        "pipeline_version": "v1",
        "config_hash": "ch",
        "input_file_hash": "ih",
        "steps": [{"name": "S1", "status": "success", "duration_ms": 10.0}],
        "success": True,
        "total_duration_ms": 10.0,
        "model_versions": {},
        "gate_history": gate_history or [],
        "terminal_routes": terminal_routes or {},
    }
