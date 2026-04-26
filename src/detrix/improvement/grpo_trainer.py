"""ART GRPO training wrapper for the Detrix improvement loop."""

from __future__ import annotations

import asyncio
import logging
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, cast

from detrix.core.trajectory import GovernedTrajectory
from detrix.improvement.sft_trainer import TrainingResult
from detrix.improvement.training_config import TrainingConfig
from detrix.runtime.trajectory_store import TrajectoryStore

logger = logging.getLogger(__name__)


Message = dict[str, str]


def trajectory_messages(trajectory: GovernedTrajectory) -> list[Message]:
    """Convert a governed trajectory into chat messages for ART-compatible tooling."""
    return [
        {
            "role": "system",
            "content": (
                "You are a domain expert agent. Produce accurate structured output "
                "that passes governance gates."
            ),
        },
        {"role": "user", "content": trajectory.prompt},
        {"role": "assistant", "content": trajectory.completion},
    ]


def _build_art_trajectory(trajectory: GovernedTrajectory) -> Any:
    from art.trajectories import Trajectory

    trajectory_type = cast(Any, Trajectory)
    try:
        return trajectory_type(history=trajectory_messages(trajectory), reward=trajectory.governance_score)
    except TypeError:
        return trajectory_type(messages=trajectory_messages(trajectory), reward=trajectory.governance_score)


def governed_to_art_group(trajectory: GovernedTrajectory) -> Any:
    """Convert a single GovernedTrajectory to an ART TrajectoryGroup.

    This helper is primarily for smoke tests and one-off inspection. Production GRPO
    should prefer grouped rollouts via ``group_governed_trajectories`` so each group has
    comparable trajectories and reward variance.
    """
    from art.trajectories import TrajectoryGroup

    trajectory_group_type = cast(Any, TrajectoryGroup)
    art_trajectory = _build_art_trajectory(trajectory)
    try:
        return trajectory_group_type(trajectories=[art_trajectory], prompt=trajectory.prompt)
    except TypeError:
        return trajectory_group_type(trajectories=[art_trajectory])


def group_governed_trajectories(trajectories: list[GovernedTrajectory]) -> list[Any]:
    """Group comparable trajectories for GRPO by prompt and require reward variance."""
    from art.trajectories import TrajectoryGroup

    trajectory_group_type = cast(Any, TrajectoryGroup)
    by_prompt: dict[str, list[GovernedTrajectory]] = defaultdict(list)
    for trajectory in trajectories:
        by_prompt[trajectory.prompt].append(trajectory)

    groups: list[Any] = []
    for prompt, prompt_trajectories in by_prompt.items():
        rewards = {trajectory.governance_score for trajectory in prompt_trajectories}
        if len(prompt_trajectories) < 2 or len(rewards) < 2:
            logger.debug("Skipping GRPO prompt group without reward variance: %s", prompt[:80])
            continue
        art_trajectories = [_build_art_trajectory(trajectory) for trajectory in prompt_trajectories]
        try:
            groups.append(trajectory_group_type(trajectories=art_trajectories, prompt=prompt))
        except TypeError:
            groups.append(trajectory_group_type(trajectories=art_trajectories))
    return groups


class DetrixGRPOTrainer:
    """ART GRPO: GovernedTrajectory -> grouped ART trajectories -> LoRA adapter."""

    def __init__(self, config: TrainingConfig) -> None:
        self.config = config

    def load_trajectory_groups(self) -> list[Any]:
        """Load governed trajectories and convert reward-varied prompt groups for ART."""
        store = TrajectoryStore(self.config.evidence_db)
        trajectories = store.query(
            domain=self.config.domain,
            min_score=self.config.min_score,
            rejection_type=None,
            limit=self.config.limit,
        )
        if not trajectories:
            raise ValueError("No trajectories match the filter criteria")

        groups = group_governed_trajectories(trajectories)
        if not groups:
            raise ValueError(
                "No GRPO trajectory groups have at least two comparable rollouts with reward variance"
            )
        logger.info("Converted %d trajectories to %d ART groups", len(trajectories), len(groups))
        return groups

    def train(self) -> TrainingResult:
        """Run GRPO training via ART local backend. Requires grpo extra and GPU."""
        if self.config.cuda_devices:
            os.environ["CUDA_VISIBLE_DEVICES"] = self.config.cuda_devices

        groups = self.load_trajectory_groups()
        adapter_path = str(Path(self.config.output_dir) / self.config.adapter_name)
        Path(adapter_path).mkdir(parents=True, exist_ok=True)

        logger.info(
            "Starting experimental ART GRPO: %d groups, model=%s",
            len(groups),
            self.config.model_name,
        )

        async def _run() -> dict[str, Any]:
            import art
            from art.local import LocalBackend

            backend = LocalBackend(path=adapter_path)
            trainable_model: Any = art.TrainableModel(
                project="detrix",
                name=Path(adapter_path).name,
                base_model=self.config.model_name,
            )
            await trainable_model.register(backend)
            await trainable_model.train(
                groups,
                config=cast(Any, {
                    "learning_rate": self.config.learning_rate,
                    "max_steps": self.config.max_steps,
                    "lora_r": self.config.lora_r,
                    "lora_alpha": self.config.lora_alpha,
                    "lora_dropout": self.config.lora_dropout,
                }),
            )
            return {"groups": float(len(groups))}

        result = asyncio.run(_run())
        metrics = {k: v for k, v in result.items() if isinstance(v, float)}
        return TrainingResult(
            adapter_path=adapter_path,
            model_name=self.config.model_name,
            backend="grpo",
            num_examples=len(groups),
            num_steps=self.config.max_steps,
            final_loss=float(result.get("loss", 0.0)),
            metrics=metrics,
        )
