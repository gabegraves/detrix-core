#!/usr/bin/env python3
"""Smoke test and A/B comparison for Detrix training loop."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
logger = logging.getLogger("smoke_train")

MODELS = {
    "27b": "/home/gabriel/models/Qwen3.6-27B-FP8",
    "35b": "/home/gabriel/models/Qwen3.6-35B-A3B-FP8",
}


def run_single(backend: str, model: str, cuda: str, max_steps: int = 2) -> dict[str, Any]:
    from detrix.improvement.training_config import TrainingConfig

    config = TrainingConfig(
        model_name=model,
        backend=backend,
        domain="xrd",
        max_steps=max_steps,
        lora_r=8,
        learning_rate=2e-4,
        logging_steps=1,
        save_steps=max_steps,
        warmup_steps=0,
        eval_split=0.0,
        cuda_devices=cuda,
    )
    if backend == "sft":
        from detrix.improvement.sft_trainer import DetrixSFTTrainer

        trainer = DetrixSFTTrainer(config)
        trainer.load_dataset()
        result = trainer.train()
    else:
        from detrix.improvement.grpo_trainer import DetrixGRPOTrainer

        trainer_grpo = DetrixGRPOTrainer(config)
        trainer_grpo.load_trajectory_groups()
        result = trainer_grpo.train()

    adapter_files = list(Path(result.adapter_path).glob("*"))
    has_safetensors = any(file.suffix == ".safetensors" for file in adapter_files)
    logger.info("RESULT: %s on %s", backend, model.split("/")[-1])
    logger.info("  Adapter: %s", result.adapter_path)
    logger.info("  Loss: %.4f", result.final_loss)
    logger.info("  Safetensors: %s", has_safetensors)
    if not has_safetensors:
        logger.error("No .safetensors found — training may have failed")
        sys.exit(1)
    (Path(result.adapter_path) / "training_result.json").write_text(
        json.dumps(result.model_dump(), indent=2, default=str)
    )
    return result.model_dump()


def ab_test(cuda: str, max_steps: int = 2) -> None:
    from detrix.improvement.promoter import ModelPromoter

    results = {}
    for name, model_path in MODELS.items():
        if not Path(model_path).exists():
            logger.warning("Skipping %s; model path does not exist: %s", name, model_path)
            continue
        results[name] = run_single("sft", model_path, cuda, max_steps)
    if {"27b", "35b"} - results.keys():
        raise SystemExit("A/B test requires both model paths to exist")

    promoter = ModelPromoter(metric_names=["neg_final_loss"])
    challenger = {"neg_final_loss": -float(results["35b"]["final_loss"])}
    incumbent = {"neg_final_loss": -float(results["27b"]["final_loss"])}
    promotion = promoter.compare(challenger, incumbent, threshold=0.05)
    logger.info("A/B TEST RESULT")
    logger.info("  27B loss: %.4f", results["27b"]["final_loss"])
    logger.info("  35B loss: %.4f", results["35b"]["final_loss"])
    logger.info("  Verdict: %s", promotion.verdict.value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Detrix training smoke test")
    parser.add_argument("--backend", choices=["sft", "grpo"], default="sft")
    parser.add_argument("--model", default=MODELS["27b"])
    parser.add_argument("--cuda", default="2", help="CUDA_VISIBLE_DEVICES")
    parser.add_argument("--max-steps", type=int, default=2)
    parser.add_argument("--ab-test", action="store_true", help="Run A/B: 27B vs 35B")
    args = parser.parse_args()
    if args.ab_test:
        ab_test(args.cuda, args.max_steps)
    else:
        run_single(args.backend, args.model, args.cuda, args.max_steps)


if __name__ == "__main__":
    main()
