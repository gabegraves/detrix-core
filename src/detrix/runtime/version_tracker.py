"""Version fingerprints for governance trace epochs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from detrix.core.trajectory import GovernedTrajectory

VERSION_CONTAMINATED_REJECTION = "version_contaminated"


@dataclass(frozen=True)
class VersionFingerprint:
    """Stable hash of evaluator and gate versions for a trace epoch."""

    evaluator_versions: dict[str, str]
    gate_versions: dict[str, str]

    @classmethod
    def from_trajectory(cls, trajectory: GovernedTrajectory) -> VersionFingerprint:
        return cls(
            evaluator_versions=dict(trajectory.evaluator_versions),
            gate_versions=dict(trajectory.gate_versions),
        )

    @property
    def hash(self) -> str:
        payload = {
            "evaluator_versions": self.evaluator_versions,
            "gate_versions": self.gate_versions,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def to_json(self) -> str:
        return json.dumps(
            {
                "evaluator_versions": self.evaluator_versions,
                "gate_versions": self.gate_versions,
                "hash": self.hash,
            },
            sort_keys=True,
        )
