"""Karpathy-style autoresearch loop for Detrix training hyperparameters."""

from __future__ import annotations

import json
import logging
import math
import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from detrix.improvement.training_config import TrainingConfig

logger = logging.getLogger(__name__)

TUNABLE_PARAMS: dict[str, dict[str, Any]] = {
    "learning_rate": {"type": "log_uniform", "low": 1e-5, "high": 1e-3},
    "lora_r": {"type": "choice", "values": [4, 8, 16, 32, 64]},
    "lora_alpha": {"type": "choice", "values": [8, 16, 32, 64]},
    "lora_dropout": {"type": "uniform", "low": 0.0, "high": 0.15},
    "gradient_accumulation_steps": {"type": "choice", "values": [1, 2, 4, 8]},
    "warmup_steps": {"type": "choice", "values": [0, 5, 10, 20]},
}


@dataclass
class ExperimentResult:
    """Result of one time-boxed training experiment."""

    experiment_num: int
    params: dict[str, Any]
    metric: float
    adapter_path: str
    kept: bool


class AutoresearchLoop:
    """Run N hyperparameter experiments and keep the best adapter."""

    def __init__(self, base_config: TrainingConfig, max_experiments: int = 50, seed: int = 42) -> None:
        self.base_config = base_config
        self.max_experiments = max_experiments
        self.rng = random.Random(seed)
        self.results: list[ExperimentResult] = []
        self.best_metric = -1.0
        self.best_adapter = ""

    def _baseline_params(self) -> dict[str, Any]:
        return {
            "learning_rate": self.base_config.learning_rate,
            "lora_r": self.base_config.lora_r,
            "lora_alpha": self.base_config.lora_alpha,
            "lora_dropout": self.base_config.lora_dropout,
            "gradient_accumulation_steps": self.base_config.gradient_accumulation_steps,
            "warmup_steps": self.base_config.warmup_steps,
        }

    def _generate_variant(self, baseline: dict[str, Any], experiment_num: int) -> dict[str, Any]:
        variant = dict(baseline)
        num_mutations = self.rng.randint(1, min(3, len(TUNABLE_PARAMS)))
        for key in self.rng.sample(list(TUNABLE_PARAMS.keys()), num_mutations):
            spec = TUNABLE_PARAMS[key]
            if spec["type"] == "log_uniform":
                variant[key] = math.exp(self.rng.uniform(math.log(spec["low"]), math.log(spec["high"])))
            elif spec["type"] == "uniform":
                variant[key] = self.rng.uniform(spec["low"], spec["high"])
            elif spec["type"] == "choice":
                variant[key] = self.rng.choice(spec["values"])
        if variant == baseline:
            variant["learning_rate"] = baseline["learning_rate"] * (1.0 + 0.1 * experiment_num)
        return variant

    def _make_config(self, params: dict[str, Any], experiment_num: int) -> TrainingConfig:
        return self.base_config.model_copy(
            update={
                "learning_rate": params["learning_rate"],
                "lora_r": params["lora_r"],
                "lora_alpha": params["lora_alpha"],
                "lora_dropout": params["lora_dropout"],
                "gradient_accumulation_steps": params["gradient_accumulation_steps"],
                "warmup_steps": params["warmup_steps"],
                "save_steps": self.base_config.max_steps,
                "eval_split": 0.0,
                "seed": self.base_config.seed + experiment_num,
            }
        )

    def best_result(self) -> ExperimentResult:
        if not self.results:
            raise ValueError("No experiments have completed")
        return max(self.results, key=lambda result: result.metric)

    def run(self, eval_fn: Callable[[str], float] | None = None) -> ExperimentResult:
        """Run the loop; use held-out governance eval when supplied, else inverse loss."""
        baseline = self._baseline_params()
        for index in range(self.max_experiments):
            params = baseline if index == 0 else self._generate_variant(baseline, index)
            config = self._make_config(params, index)
            if config.backend == "sft":
                from detrix.improvement.sft_trainer import DetrixSFTTrainer

                trainer: Any = DetrixSFTTrainer(config)
                trainer.load_dataset()
                result = trainer.train()
            else:
                from detrix.improvement.grpo_trainer import DetrixGRPOTrainer

                trainer = DetrixGRPOTrainer(config)
                trainer.load_trajectory_groups()
                result = trainer.train()

            metric = eval_fn(result.adapter_path) if eval_fn else 1.0 / (1.0 + result.final_loss)
            kept = metric > self.best_metric
            experiment = ExperimentResult(index + 1, params, metric, result.adapter_path, kept)
            self.results.append(experiment)
            if kept:
                self.best_metric = metric
                self.best_adapter = result.adapter_path
                baseline = dict(params)

        best = self.best_result()
        report_path = Path(self.base_config.output_dir) / "autoresearch_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(
                {
                    "best_experiment": best.experiment_num,
                    "best_metric": best.metric,
                    "best_adapter": best.adapter_path,
                    "best_params": best.params,
                    "metric_note": "Higher is better; default metric is inverse training loss unless eval_fn is supplied.",
                    "all_results": [
                        {
                            "num": result.experiment_num,
                            "metric": result.metric,
                            "kept": result.kept,
                            "params": result.params,
                        }
                        for result in self.results
                    ],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                indent=2,
                default=str,
            )
        )
        return best
