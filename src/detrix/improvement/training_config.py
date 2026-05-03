"""Training configuration for the Detrix improvement loop."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, computed_field


class TrainingConfig(BaseModel):
    """Configuration for SFT or GRPO training runs."""

    model_name: str
    backend: Literal["sft", "grpo"] = "sft"
    output_dir: str = ".detrix/adapters"
    evidence_db: str = ".detrix/evidence.db"

    domain: str | None = None
    min_score: float | None = None
    cuda_devices: str | None = None
    limit: int | None = None

    max_steps: int = 100
    per_device_train_batch_size: int = 1
    gradient_accumulation_steps: int = 4
    learning_rate: float = 2e-4
    max_seq_length: int = 2048
    warmup_steps: int = 10
    logging_steps: int = 10
    save_steps: int = 50

    load_in_4bit: bool = False
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    lora_target_modules: list[str] = Field(
        default_factory=lambda: [
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ]
    )

    eval_split: float = 0.1
    seed: int = 42

    @computed_field  # type: ignore[prop-decorator]
    @property
    def adapter_name(self) -> str:
        """Timestamped adapter directory name derived from model slug and backend."""
        slug = re.sub(r"[^a-zA-Z0-9._-]", "-", self.model_name.rsplit("/", 1)[-1])
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        return f"{slug}-detrix-{self.backend}-{ts}"
