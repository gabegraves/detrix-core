"""Run comparison — diff two RunArtifacts to see what changed."""

from __future__ import annotations

from pydantic import BaseModel, Field

from detrix.runtime.artifact import RunArtifact


class StepDiff(BaseModel):
    """What changed in a single step between two runs."""

    step_id: str
    input_changed: bool = False
    output_changed: bool = False
    status_changed: bool = False
    duration_delta_ms: float = 0.0
    old_status: str | None = None
    new_status: str | None = None


class DiffReport(BaseModel):
    """Complete comparison between two runs."""

    run_a_id: str
    run_b_id: str
    inputs_changed: bool = False
    outputs_changed: bool = False
    env_changed: bool = False
    steps_changed: list[StepDiff] = Field(default_factory=list)
    steps_added: list[str] = Field(default_factory=list)
    steps_removed: list[str] = Field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return (
            self.inputs_changed
            or self.outputs_changed
            or self.env_changed
            or len(self.steps_changed) > 0
            or len(self.steps_added) > 0
            or len(self.steps_removed) > 0
        )

    def format_text(self) -> str:
        """Render a human-readable diff summary."""
        lines: list[str] = []
        lines.append(f"Diff: {self.run_a_id} → {self.run_b_id}")
        lines.append("=" * 50)

        if not self.has_changes:
            lines.append("  No changes detected.")
            return "\n".join(lines)

        if self.inputs_changed:
            lines.append("  [CHANGED] Inputs hash differs")
        if self.outputs_changed:
            lines.append("  [CHANGED] Outputs hash differs")
        if self.env_changed:
            lines.append("  [CHANGED] Environment differs")

        for sd in self.steps_changed:
            parts = []
            if sd.input_changed:
                parts.append("inputs")
            if sd.output_changed:
                parts.append("outputs")
            if sd.status_changed:
                parts.append(f"status: {sd.old_status} → {sd.new_status}")
            if sd.duration_delta_ms:
                sign = "+" if sd.duration_delta_ms > 0 else ""
                parts.append(f"duration: {sign}{sd.duration_delta_ms:.0f}ms")
            lines.append(f"  [CHANGED] {sd.step_id}: {', '.join(parts)}")

        for s in self.steps_added:
            lines.append(f"  [ADDED]   {s}")
        for s in self.steps_removed:
            lines.append(f"  [REMOVED] {s}")

        return "\n".join(lines)


def diff_runs(artifact_a: RunArtifact, artifact_b: RunArtifact) -> DiffReport:
    """Compare two RunArtifacts and produce a DiffReport."""
    report = DiffReport(
        run_a_id=artifact_a.run_id,
        run_b_id=artifact_b.run_id,
        inputs_changed=artifact_a.inputs_hash != artifact_b.inputs_hash,
        outputs_changed=artifact_a.outputs_hash != artifact_b.outputs_hash,
        env_changed=artifact_a.env_spec != artifact_b.env_spec,
    )

    steps_a = {sr.step_id: sr for sr in artifact_a.step_results}
    steps_b = {sr.step_id: sr for sr in artifact_b.step_results}

    all_ids = set(steps_a.keys()) | set(steps_b.keys())
    for step_id in sorted(all_ids):
        if step_id not in steps_a:
            report.steps_added.append(step_id)
        elif step_id not in steps_b:
            report.steps_removed.append(step_id)
        else:
            sa = steps_a[step_id]
            sb = steps_b[step_id]
            input_changed = sa.input_hash != sb.input_hash
            output_changed = sa.output_hash != sb.output_hash
            status_changed = sa.status != sb.status
            duration_delta = sb.duration_ms - sa.duration_ms

            if input_changed or output_changed or status_changed:
                report.steps_changed.append(
                    StepDiff(
                        step_id=step_id,
                        input_changed=input_changed,
                        output_changed=output_changed,
                        status_changed=status_changed,
                        duration_delta_ms=duration_delta,
                        old_status=sa.status.value if status_changed else None,
                        new_status=sb.status.value if status_changed else None,
                    )
                )

    return report
