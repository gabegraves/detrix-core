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
        self.store.mark_exported([trajectory.trajectory_id for trajectory in trajectories])
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
        self.store.mark_exported([trajectory.trajectory_id for trajectory in trajectories])
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
        exported_positive_ids: list[str] = []
        with path.open("w", encoding="utf-8") as file:
            for positive_trajectory in positive:
                wrote_pair = False
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
                    wrote_pair = True
                if wrote_pair:
                    exported_positive_ids.append(positive_trajectory.trajectory_id)
        self.store.mark_exported(exported_positive_ids)
        return str(path)

    def export_routed(
        self,
        output_dir: str,
        domain: str | None = None,
        limit: int | None = None,
    ) -> dict[str, str]:
        """Export trajectories by their portable admission training_route field."""
        trajectories = self.store.query(domain=domain, limit=limit)
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)
        paths = {
            "sft": root / "routed.sft.jsonl",
            "dpo": root / "routed.dpo.jsonl",
            "grpo": root / "routed.grpo.jsonl",
            "eval_only": root / "routed.eval_only.jsonl",
        }
        exported_ids: list[str] = []
        with (
            paths["sft"].open("w", encoding="utf-8") as sft,
            paths["dpo"].open("w", encoding="utf-8") as dpo,
            paths["grpo"].open("w", encoding="utf-8") as grpo,
            paths["eval_only"].open("w", encoding="utf-8") as eval_only,
        ):
            for trajectory in trajectories:
                route = trajectory.training_route or (
                    "eval_only" if trajectory.rejection_type else "sft"
                )
                if route == "sft":
                    sft.write(json.dumps(trajectory.to_sft_row()) + "\n")
                    grpo.write(json.dumps(trajectory.to_grpo_row()) + "\n")
                    exported_ids.append(trajectory.trajectory_id)
                elif route == "dpo":
                    dpo.write(json.dumps(_dpo_row_from_trajectory(trajectory)) + "\n")
                    exported_ids.append(trajectory.trajectory_id)
                else:
                    eval_only.write(json.dumps(trajectory.model_dump(mode="json")) + "\n")
        self.store.mark_exported(exported_ids)
        return {route: str(path) for route, path in paths.items()}

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
            self.store.mark_exported([trajectory.trajectory_id for trajectory in trajectories])
        elif format == "grpo":
            trajectories = self.store.query(
                domain=domain,
                min_score=min_score,
                rejection_type=None,
                limit=limit,
            )
            rows = [trajectory.to_grpo_row() for trajectory in trajectories]
            self.store.mark_exported([trajectory.trajectory_id for trajectory in trajectories])
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


def _dpo_row_from_trajectory(trajectory: Any) -> dict[str, str]:
    chosen = _suggest_rewrite(trajectory.completion)
    return {
        "prompt": trajectory.prompt,
        "chosen": chosen,
        "rejected": trajectory.completion,
    }


def _suggest_rewrite(text: str) -> str:
    if "•" in text and "\n•" not in text:
        parts = [part.strip() for part in text.split("•") if part.strip()]
        if len(parts) > 1:
            return parts[0] + "\n" + "\n".join(f"• {part}" for part in parts[1:])
    paragraphs = [text[i : i + 500].strip() for i in range(0, len(text), 500)]
    return "\n\n".join(part for part in paragraphs if part)
