from __future__ import annotations

from detrix.improvement.training_config import TrainingConfig


class TestTrainingConfig:
    def test_default_config(self) -> None:
        config = TrainingConfig(model_name="test/model")
        assert config.model_name == "test/model"
        assert config.backend == "sft"
        assert config.max_steps == 100
        assert config.lora_r == 16
        assert config.output_dir == ".detrix/adapters"

    def test_grpo_backend(self) -> None:
        config = TrainingConfig(model_name="test/model", backend="grpo")
        assert config.backend == "grpo"
        assert "grpo" in config.adapter_name

    def test_adapter_name_includes_model_slug(self) -> None:
        config = TrainingConfig(model_name="/home/user/models/Qwen3.6-27B-FP8")
        assert "Qwen3.6-27B-FP8" in config.adapter_name
        assert "sft" in config.adapter_name

    def test_blackwell_gpu_defaults(self) -> None:
        config = TrainingConfig(model_name="test/model", cuda_devices="2")
        assert config.cuda_devices == "2"

    def test_config_with_overrides(self) -> None:
        config = TrainingConfig(
            model_name="qwen/test",
            backend="grpo",
            max_steps=2,
            lora_r=64,
            learning_rate=1e-5,
            domain="xrd",
            min_score=0.8,
        )
        assert config.max_steps == 2
        assert config.lora_r == 64
        assert config.learning_rate == 1e-5
        assert config.domain == "xrd"
