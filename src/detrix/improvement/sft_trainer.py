"""Unsloth SFT training wrapper for the Detrix improvement loop."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from detrix.improvement.exporter import TrainingExporter
from detrix.improvement.training_config import TrainingConfig
from detrix.runtime.trajectory_store import TrajectoryStore

logger = logging.getLogger(__name__)


class TrainingResult(BaseModel):
    """Outcome of a training run."""

    adapter_path: str
    model_name: str
    backend: str
    num_examples: int
    num_steps: int
    final_loss: float
    metrics: dict[str, float] = Field(default_factory=dict)


class DetrixSFTTrainer:
    """Unsloth + TRL SFTTrainer: TrajectoryStore -> HF Dataset -> LoRA adapter."""

    def __init__(self, config: TrainingConfig) -> None:
        self.config = config

    @staticmethod
    def format_chat(row: dict[str, str]) -> str:
        """Format prompt/completion rows as ChatML for Qwen-family instruction tuning."""
        return (
            "<|im_start|>system\n"
            "You are a domain expert agent. Produce accurate structured output "
            "that passes governance gates.<|im_end|>\n"
            f"<|im_start|>user\n{row['prompt']}<|im_end|>\n"
            f"<|im_start|>assistant\n{row['completion']}<|im_end|>\n"
        )

    def load_dataset(self) -> Any:
        """Load governed trajectories as a HuggingFace Dataset with a text column."""
        store = TrajectoryStore(self.config.evidence_db)
        exporter = TrainingExporter(store)
        dataset = exporter.to_dataset(
            "sft",
            domain=self.config.domain,
            min_score=self.config.min_score,
            limit=self.config.limit,
        )
        if len(dataset) == 0:
            raise ValueError("No trajectories match the filter criteria")
        return dataset.map(lambda row: {"text": self.format_chat(row)})

    def train(self) -> TrainingResult:
        """Run the full Unsloth SFT training loop. Requires trainer extra and GPU."""
        if self.config.cuda_devices:
            os.environ["CUDA_VISIBLE_DEVICES"] = self.config.cuda_devices

        from unsloth import FastLanguageModel

        dataset = self.load_dataset()
        logger.info("Loaded %d training examples", len(dataset))

        if self.config.eval_split > 0 and len(dataset) > 1:
            split = dataset.train_test_split(test_size=self.config.eval_split, seed=self.config.seed)
            train_dataset = split["train"]
            eval_dataset = split["test"]
        else:
            train_dataset = dataset
            eval_dataset = None

        logger.info("Loading model via Unsloth: %s", self.config.model_name)
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=self.config.model_name,
            max_seq_length=self.config.max_seq_length,
            load_in_4bit=self.config.load_in_4bit,
        )
        model = FastLanguageModel.get_peft_model(
            model,
            r=self.config.lora_r,
            lora_alpha=self.config.lora_alpha,
            lora_dropout=self.config.lora_dropout,
            target_modules=self.config.lora_target_modules,
        )

        if getattr(tokenizer, "pad_token", None) is None:
            tokenizer.pad_token = tokenizer.eos_token

        adapter_path = str(Path(self.config.output_dir) / self.config.adapter_name)
        training_args = self._training_args(adapter_path, eval_dataset is not None)

        from trl import SFTTrainer

        trainer_kwargs: dict[str, Any] = {
            "model": model,
            "args": training_args,
            "train_dataset": train_dataset,
            "eval_dataset": eval_dataset,
            "processing_class": tokenizer,
        }
        trainer = SFTTrainer(**trainer_kwargs)

        logger.info("Starting Unsloth SFT: %d steps", self.config.max_steps)
        train_result = trainer.train()
        trainer.save_model(adapter_path)
        tokenizer.save_pretrained(adapter_path)

        metrics: dict[str, float] = {}
        if eval_dataset is not None:
            try:
                eval_metrics = trainer.evaluate()
                metrics = {k: v for k, v in eval_metrics.items() if isinstance(v, float)}
            except RuntimeError as exc:
                if "out of memory" not in str(exc).lower():
                    raise
                logger.warning("Skipping post-train evaluation after CUDA OOM: %s", exc)
                metrics = {"eval_oom": 1.0}

        final_loss = float(getattr(train_result, "training_loss", 0.0) or 0.0)
        return TrainingResult(
            adapter_path=adapter_path,
            model_name=self.config.model_name,
            backend="sft",
            num_examples=len(train_dataset),
            num_steps=self.config.max_steps,
            final_loss=final_loss,
            metrics=metrics,
        )

    def _training_args(self, output_dir: str, has_eval: bool) -> Any:
        """Build TRL training args with compatibility across recent TRL versions."""
        try:
            from trl import SFTConfig

            return SFTConfig(
                output_dir=output_dir,
                max_steps=self.config.max_steps,
                per_device_train_batch_size=self.config.per_device_train_batch_size,
                gradient_accumulation_steps=self.config.gradient_accumulation_steps,
                learning_rate=self.config.learning_rate,
                warmup_steps=self.config.warmup_steps,
                logging_steps=self.config.logging_steps,
                save_steps=self.config.save_steps,
                save_total_limit=2,
                bf16=self._bf16_supported(),
                seed=self.config.seed,
                report_to="none",
                eval_strategy="steps" if has_eval else "no",
                eval_steps=self.config.save_steps if has_eval else None,
                max_length=self.config.max_seq_length,
                packing=False,
            )
        except ImportError:
            from transformers import TrainingArguments

            return TrainingArguments(
                output_dir=output_dir,
                max_steps=self.config.max_steps,
                per_device_train_batch_size=self.config.per_device_train_batch_size,
                gradient_accumulation_steps=self.config.gradient_accumulation_steps,
                learning_rate=self.config.learning_rate,
                warmup_steps=self.config.warmup_steps,
                logging_steps=self.config.logging_steps,
                save_steps=self.config.save_steps,
                save_total_limit=2,
                bf16=self._bf16_supported(),
                seed=self.config.seed,
                report_to="none",
                eval_strategy="steps" if has_eval else "no",
                eval_steps=self.config.save_steps if has_eval else None,
            )

    @staticmethod
    def _bf16_supported() -> bool:
        """Enable bf16 only on CUDA devices that explicitly support it."""
        try:
            import torch

            return bool(torch.cuda.is_available() and torch.cuda.is_bf16_supported())
        except Exception:
            return False
