"""Training data export from governed trajectories."""

from __future__ import annotations

import json
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

from detrix.runtime.trajectory_store import TrajectoryStore


class TrainingExporter:
    """Export governed trajectories as training data for SFT, DPO, and GRPO."""

    def __init__(self, store: TrajectoryStore) -> None:
        self.store = store

    def export_sft(
        self,
        output_path: str,
        domain: str | None = None,
        min_score: float | None = None,
        limit: int | None = None,
    ) -> str:
        """Export passing trajectories as SFT JSONL prompt/completion pairs."""
        trajectories = self.store.query(
            domain=domain,
            min_score=min_score,
            rejection_type=None,
            limit=limit,
        )
        path = self._prepare_output(output_path)
        with path.open("w", encoding="utf-8") as file:
            for trajectory in trajectories:
                file.write(json.dumps(trajectory.to_sft_row()) + "\n")
        return str(path)

    def export_grpo(
        self,
        output_path: str,
        domain: str | None = None,
        min_score: float | None = None,
        limit: int | None = None,
    ) -> str:
        """Export passing trajectories as GRPO JSONL with governance scores."""
        trajectories = self.store.query(
            domain=domain,
            min_score=min_score,
            rejection_type=None,
            limit=limit,
        )
        path = self._prepare_output(output_path)
        with path.open("w", encoding="utf-8") as file:
            for trajectory in trajectories:
                file.write(json.dumps(trajectory.to_grpo_row()) + "\n")
        return str(path)

    def export_dpo(
        self,
        output_path: str,
        domain: str | None = None,
        limit: int | None = None,
    ) -> str:
        """Export DPO pairs by matching accepted and output-rejected rows by prompt."""
        positive = self.store.query(domain=domain, rejection_type=None, limit=limit)
        negative = self.store.query(domain=domain, rejection_type="output_quality", limit=limit)

        negative_by_prompt: dict[str, list[Any]] = defaultdict(list)
        for trajectory in negative:
            negative_by_prompt[trajectory.prompt].append(trajectory)

        path = self._prepare_output(output_path)
        with path.open("w", encoding="utf-8") as file:
            for positive_trajectory in positive:
                for negative_trajectory in negative_by_prompt.get(
                    positive_trajectory.prompt,
                    [],
                ):
                    file.write(
                        json.dumps(
                            {
                                "prompt": positive_trajectory.prompt,
                                "chosen": positive_trajectory.completion,
                                "rejected": negative_trajectory.completion,
                            }
                        )
                        + "\n"
                    )
        return str(path)

    def to_dataset(
        self,
        format: str,
        domain: str | None = None,
        min_score: float | None = None,
        limit: int | None = None,
    ) -> Any:
        """Export directly to a HuggingFace Dataset object."""
        from datasets import Dataset

        if format == "sft":
            trajectories = self.store.query(
                domain=domain,
                min_score=min_score,
                rejection_type=None,
                limit=limit,
            )
            rows = [trajectory.to_sft_row() for trajectory in trajectories]
        elif format == "grpo":
            trajectories = self.store.query(
                domain=domain,
                min_score=min_score,
                rejection_type=None,
                limit=limit,
            )
            rows = [trajectory.to_grpo_row() for trajectory in trajectories]
        elif format == "dpo":
            with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp:
                tmp_path = Path(tmp.name)
            try:
                self.export_dpo(str(tmp_path), domain=domain, limit=limit)
                rows = [json.loads(line) for line in tmp_path.read_text().splitlines()]
            finally:
                tmp_path.unlink(missing_ok=True)
        else:
            raise ValueError(f"Unknown format: {format}. Use 'sft', 'grpo', or 'dpo'.")

        return Dataset.from_list(rows) if rows else Dataset.from_dict({})

    @staticmethod
    def _prepare_output(output_path: str) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
