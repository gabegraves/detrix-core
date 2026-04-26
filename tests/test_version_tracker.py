from __future__ import annotations

from datetime import datetime, timezone

from detrix.core.trajectory import GovernedTrajectory
from detrix.runtime.trajectory_store import TrajectoryStore
from detrix.runtime.version_tracker import VERSION_CONTAMINATED_REJECTION, VersionFingerprint


def _trajectory(tid: str, version: str) -> GovernedTrajectory:
    return GovernedTrajectory(
        trajectory_id=tid,
        run_id="run",
        domain="xrd",
        prompt=f"prompt-{tid}",
        completion=f"completion-{tid}",
        verdicts=[{"decision": "accept", "gate_id": "gate", "evidence": {}}],
        governance_score=1.0,
        gate_pass_rate=1.0,
        evaluator_versions={"eval": version},
        gate_versions={"gate": version},
        started_at=datetime(2026, 4, 26, tzinfo=timezone.utc),
    )


def test_version_fingerprint_is_stable() -> None:
    a = VersionFingerprint({"b": "2", "a": "1"}, {"gate": "1"})
    b = VersionFingerprint({"a": "1", "b": "2"}, {"gate": "1"})
    assert a.hash == b.hash


def test_version_change_contaminates_unexported_clean_traces(tmp_path) -> None:
    store = TrajectoryStore(str(tmp_path / "evidence.db"))
    store.append(_trajectory("old", "1"))
    store.append(_trajectory("new", "2"))

    old = store.get("old")
    new = store.get("new")

    assert old is not None
    assert old.rejection_type == VERSION_CONTAMINATED_REJECTION
    assert new is not None
    assert new.rejection_type is None
    assert store.query(rejection_type=None) == [new]


def test_exported_traces_are_not_contaminated_on_later_version_change(tmp_path) -> None:
    from detrix.improvement.exporter import TrainingExporter

    store = TrajectoryStore(str(tmp_path / "evidence.db"))
    store.append(_trajectory("old", "1"))
    TrainingExporter(store).export_sft(str(tmp_path / "sft.jsonl"), domain="xrd")

    store.append(_trajectory("new", "2"))

    old = store.get("old")
    assert old is not None
    assert old.rejection_type is None


def test_legacy_unversioned_traces_are_contaminated_before_new_epoch(tmp_path) -> None:
    import sqlite3

    db_path = tmp_path / "legacy.db"
    legacy = _trajectory("legacy", "legacy")
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE governed_trajectories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trajectory_id TEXT NOT NULL UNIQUE,
                run_id TEXT NOT NULL,
                domain TEXT NOT NULL,
                schema_version INTEGER NOT NULL,
                governance_score REAL NOT NULL,
                gate_pass_rate REAL NOT NULL,
                rejection_type TEXT,
                model_version TEXT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                trajectory_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute(
            """INSERT INTO governed_trajectories
               (trajectory_id, run_id, domain, schema_version, governance_score,
                gate_pass_rate, rejection_type, model_version, started_at,
                finished_at, trajectory_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                legacy.trajectory_id,
                legacy.run_id,
                legacy.domain,
                legacy.schema_version,
                legacy.governance_score,
                legacy.gate_pass_rate,
                legacy.rejection_type,
                legacy.model_version,
                legacy.started_at.isoformat(),
                None,
                legacy.model_dump_json(),
            ),
        )

    store = TrajectoryStore(str(db_path))
    store.append(_trajectory("new", "2"))

    contaminated = store.get("legacy")
    assert contaminated is not None
    assert contaminated.rejection_type == VERSION_CONTAMINATED_REJECTION
    assert [trajectory.trajectory_id for trajectory in store.query(rejection_type=None)] == ["new"]
