# Qwen 3.6 OpenClaw Improvement Proof — 2026-05-03

## Result

We have **post-training target-likelihood proof that the Qwen3.6-27B-FP8 LoRA adapter moved the model toward the governed OpenClaw targets**, but we do **not** have behavior-level promotion yet.

- **Model-improvement proof:** pass on held-out teacher-forced target likelihood.
- **Deployment/promotion proof:** fail on greedy `temperature=0` generation gates.
- **Decision:** treat the adapter as `training_improved / behavior_not_promoted`; keep it out of promoted runtime until a generation replay clears deterministic gates without precision regression.

This distinction is intentional: Detrix should prove that training changed the model in the intended direction, then separately require gates/replay before admitting the behavior.

## Why gates + hooks + skills + post-training is the right solution

1. **Hooks** capture tool results, traces, evidence packets, and candidate transitions without constraining the agent's action space.
2. **Deterministic gates** score outputs post-hoc and prevent false promotion. The harness now treats empty generations as hard rejects.
3. **Skills** are the cheapest first improvement lever when a failure is procedural or tool-use related.
4. **SFT/LoRA post-training** is appropriate only after traces survive admission and can be replayed against held-out cases.
5. **Promotion** must be replay-gated: target-likelihood improvement is not enough to deploy if greedy behavior is still bad.

## Commands and artifacts

### SFT adapter trained on Blackwell GPUs

```bash
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=0,1 uv run detrix train --backend sft \
  --model /home/gabriel/models/Qwen3.6-27B-FP8 \
  --domain openclaw --limit 48 --max-steps 12 --lora-r 8 --learning-rate 3e-4 \
  --output-dir /tmp/detrix-qwen-proof/adapters-chatend \
  --db /tmp/detrix-qwen-proof/evidence-rich.db
```

Adapter:

```text
/tmp/detrix-qwen-proof/adapters-chatend/Qwen3.6-27B-FP8-detrix-sft-20260503-102728
```

Training completed and saved the adapter. Post-train `trainer.evaluate()` hit CUDA OOM; `sft_trainer.py` now records that condition without discarding the saved adapter.

### Held-out target-likelihood proof

```bash
CUDA_VISIBLE_DEVICES=0,1 uv run detrix openclaw score-improvement \
  /tmp/detrix-qwen-proof/cases-target.jsonl \
  --model /home/gabriel/models/Qwen3.6-27B-FP8 \
  --adapter /tmp/detrix-qwen-proof/adapters-chatend/Qwen3.6-27B-FP8-detrix-sft-20260503-102728 \
  --json-output /tmp/detrix-qwen-proof/target-score-chatend-final.json \
  --min-loss-delta 0.01
```

Result:

```text
baseline mean_loss:   13.5163
challenger mean_loss: 7.0595
loss_delta:           +6.4568
Proof type:           target_likelihood
Improved: true
Promotion allowed: false
```

Report:

```text
/tmp/detrix-qwen-proof/target-score-chatend-final.json
```

### Greedy behavior replay proof

Baseline generation:

```bash
CUDA_VISIBLE_DEVICES=0,1 uv run detrix openclaw generate-proof \
  /tmp/detrix-qwen-proof/cases.jsonl \
  --model /home/gabriel/models/Qwen3.6-27B-FP8 \
  --output /tmp/detrix-qwen-proof/baseline.jsonl \
  --max-new-tokens 120
```

Adapter generation:

```bash
CUDA_VISIBLE_DEVICES=0,1 uv run detrix openclaw generate-proof \
  /tmp/detrix-qwen-proof/cases.jsonl \
  --model /home/gabriel/models/Qwen3.6-27B-FP8 \
  --adapter /tmp/detrix-qwen-proof/adapters-chatend/Qwen3.6-27B-FP8-detrix-sft-20260503-102728 \
  --output /tmp/detrix-qwen-proof/challenger-chatend.jsonl \
  --max-new-tokens 80
```

Gate evaluation:

```bash
uv run detrix openclaw eval-improvement \
  /tmp/detrix-qwen-proof/cases.jsonl \
  --baseline /tmp/detrix-qwen-proof/baseline.jsonl \
  --challenger /tmp/detrix-qwen-proof/challenger-chatend.jsonl \
  --json-output /tmp/detrix-qwen-proof/report-chatend.json \
  --max-paragraph 160
```

Result:

```text
baseline mean_gate_score:   0.500
challenger mean_gate_score: 0.500
expected_contains_rate:    0.000 -> 0.000
promotion_allowed:         false
```

The adapter improved target likelihood but still emits invalid repetitive/garbled greedy text, so Detrix correctly refuses promotion.

## False-proof avoided

A stronger 30-step run overfit into empty outputs. Empty outputs originally looked superficially cleaner to readability gates; the proof harness now hard-rejects empty output with reason `empty_output`, and challenger hard rejects cannot promote even when the baseline also rejects.

Report:

```text
/tmp/detrix-qwen-proof/report-rich-v2.json
```

Key result:

```text
challenger reject_rate: 1.0
reason_counts: {"empty_output": 3}
promotion_allowed: false
```

## Implementation touchpoints

- `src/detrix/openclaw/improvement_proof.py` — proof cases, generated-output scoring, target-likelihood scoring, empty-output rejection, greedy Qwen generation.
- `src/detrix/cli/main.py` — `detrix openclaw generate-proof`, `eval-improvement`, and `score-improvement` commands.
- `src/detrix/improvement/sft_trainer.py` — keeps saved adapters when post-train evaluation OOMs.
- `src/detrix/improvement/training_config.py` — expands LoRA targets to attention + MLP modules for meaningful adaptation.
- `tests/test_openclaw_improvement_proof.py` and `tests/test_openclaw_improvement_cli.py` — synthetic promotion, empty-output rejection, target-score comparison, and CLI promotion tests.

## Next promotion requirement

The next proof target is not more generic training. It is a behavior-clearing adapter or runtime fix:

1. Verify a Qwen3.6-class text/instruct checkpoint can produce non-garbled baseline text under the local stack.
2. Keep `do_sample=False` for deterministic `temperature=0` replay.
3. Train only on admitted rows.
4. Promote only if greedy replay improves deterministic gates and has no false-accept/precision regression.
