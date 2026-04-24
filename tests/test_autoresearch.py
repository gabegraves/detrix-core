from __future__ import annotations

from detrix.improvement.autoresearch import AutoresearchLoop, ExperimentResult
from detrix.improvement.training_config import TrainingConfig


class TestAutoresearchLoop:
    def test_generate_hyperparams_varies_from_baseline(self) -> None:
        loop = AutoresearchLoop(TrainingConfig(model_name="test/model"), max_experiments=5)
        baseline = loop._baseline_params()
        variant = loop._generate_variant(baseline, experiment_num=1)
        assert variant != baseline

    def test_experiment_result_structure(self) -> None:
        result = ExperimentResult(
            experiment_num=1,
            params={"learning_rate": 2e-4, "lora_r": 16},
            metric=0.85,
            adapter_path="/path/to/adapter",
            kept=True,
        )
        assert result.kept is True
        assert result.metric == 0.85

    def test_loop_tracks_best(self) -> None:
        loop = AutoresearchLoop(TrainingConfig(model_name="test/model"), max_experiments=3)
        loop.results = [
            ExperimentResult(1, {"lr": 1e-4}, 0.7, "/a", False),
            ExperimentResult(2, {"lr": 2e-4}, 0.9, "/b", True),
            ExperimentResult(3, {"lr": 3e-4}, 0.8, "/c", False),
        ]
        assert loop.best_result().experiment_num == 2
        assert loop.best_result().metric == 0.9
