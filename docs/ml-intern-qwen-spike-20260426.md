# Manual Qwen3.6/Unsloth spike via ml-intern context

Date: 2026-04-26
Bead: `detrix-core-82i.1`
Related blocker: `detrix-core-9wp`

## Privacy posture

This spike used existing Detrix synthetic governed trajectories in `.detrix/evidence.db` only. No proprietary/customer inputs were provided to ml-intern. A governed ml-intern run was not attempted because no local ml-intern source checkout was present under `/home/gabriel`, and global/headless ml-intern is forbidden for governed work by the policy in `docs/ml-intern-governed-worker.md`.

## Environment evidence

Installed package versions:

- `transformers==4.57.1`
- `unsloth==2025.11.2`
- `torch==2.9.1`
- `trl==0.18.2`
- `peft==0.17.1`
- `accelerate==1.11.0`

Local model config:

- Path: `/home/gabriel/models/Qwen3.6-27B-FP8/config.json`
- `model_type = qwen3_5`
- `architectures = ["Qwen3_5ForConditionalGeneration"]`
- `transformers_version = 4.57.1`
- `quantization_config.quant_method = fp8`

`AutoConfig.from_pretrained('/home/gabriel/models/Qwen3.6-27B-FP8', trust_remote_code=True)` still fails with Transformers not recognizing `model_type=qwen3_5`, even though `qwen3` is present in `CONFIG_MAPPING`.

## Smoke attempt

Command:

```bash
uv run python scripts/smoke_train.py \
  --backend sft \
  --model /home/gabriel/models/Qwen3.6-27B-FP8 \
  --max-steps 2
```

Outcome: failed before adapter save; no `.safetensors` or `training_result.json` emitted.

Observed failure:

```text
ValueError: Unsloth: FP8 quantization is only supported on L4 and higher GPUs with compute capability 8.9 or higher. You are using NVIDIA GeForce RTX 3090.
```

This run also confirmed that two synthetic training examples load from `TrajectoryStore` and map through the SFT dataset path before model loading.

## Interpretation

There are two compatibility issues to track:

1. Transformers 4.57.1 does not recognize the local checkpoint `model_type=qwen3_5` through plain `AutoConfig`.
2. The current Unsloth path reaches FP8 hardware validation and rejects RTX 3090 for this FP8 checkpoint.

## Next action

Use a non-FP8 or BF16 Qwen-family checkpoint for the next two-step adapter smoke, or run the FP8 checkpoint on hardware with compute capability >= 8.9. Separately test a source-built Transformers version that recognizes `qwen3_5` before treating the local Qwen3.6 FP8 checkpoint as generally compatible.
