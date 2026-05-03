"""Baseline-vs-adapter improvement proof for OpenClaw readability behavior."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel, Field

from detrix.core.governance import Decision, GateContext
from detrix.openclaw.gates import OpenClawGovernanceGate


class ProofCase(BaseModel):
    """A held-out prompt used for deterministic model-improvement replay."""

    case_id: str
    prompt: str
    target_completion: str | None = None
    expected_contains: list[str] = Field(default_factory=list)
    forbidden_contains: list[str] = Field(default_factory=list)


class CandidateMetrics(BaseModel):
    """Gate and reference metrics for one model candidate."""

    name: str
    total: int
    accept_rate: float
    caution_rate: float
    reject_rate: float
    mean_gate_score: float
    expected_contains_rate: float
    forbidden_absent_rate: float
    outputs: dict[str, str] = Field(default_factory=dict)
    reason_counts: dict[str, int] = Field(default_factory=dict)


class ImprovementProofReport(BaseModel):
    """Promotion-style comparison for a challenger adapter."""

    baseline: CandidateMetrics
    challenger: CandidateMetrics
    metric_deltas: dict[str, float]
    improved: bool
    precision_regression: bool
    promotion_allowed: bool
    temperature: float
    decoding: str


@dataclass(frozen=True)
class GeneratedOutput:
    """Generated text for one held-out case."""

    case_id: str
    output: str


class TargetScore(BaseModel):
    """Teacher-forced loss for a model on proof targets."""

    name: str
    mean_loss: float
    case_losses: dict[str, float]


class TargetScoreReport(BaseModel):
    """Baseline-vs-adapter teacher-forced target likelihood proof."""

    proof_type: str = "target_likelihood"
    baseline: TargetScore
    challenger: TargetScore
    loss_delta: float
    improved: bool
    promotion_allowed: bool = False


def load_cases(path: str | Path) -> list[ProofCase]:
    """Load held-out proof cases from JSONL."""
    cases: list[ProofCase] = []
    with Path(path).open(encoding="utf-8") as file:
        for line in file:
            raw = line.strip()
            if raw:
                cases.append(ProofCase.model_validate_json(raw))
    return cases


def write_outputs(path: str | Path, outputs: Sequence[GeneratedOutput]) -> str:
    """Persist generated outputs as JSONL."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for item in outputs:
            file.write(json.dumps({"case_id": item.case_id, "output": item.output}) + "\n")
    return str(output_path)


def load_outputs(path: str | Path) -> dict[str, str]:
    """Load generated outputs keyed by case_id."""
    outputs: dict[str, str] = {}
    with Path(path).open(encoding="utf-8") as file:
        for line in file:
            raw = line.strip()
            if not raw:
                continue
            payload = json.loads(raw)
            case_id = str(payload["case_id"])
            if case_id in outputs:
                raise ValueError(f"Duplicate generated output for case_id={case_id}")
            outputs[case_id] = str(payload["output"])
    return outputs


def validate_output_coverage(cases: Sequence[ProofCase], outputs: dict[str, str]) -> None:
    """Fail closed unless generated outputs exactly cover held-out proof cases."""
    expected = {case.case_id for case in cases}
    actual = set(outputs)
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing or unexpected:
        details: list[str] = []
        if missing:
            details.append(f"missing={missing}")
        if unexpected:
            details.append(f"unexpected={unexpected}")
        raise ValueError("Generated outputs do not match proof cases: " + ", ".join(details))


def evaluate_candidate(
    name: str,
    cases: Sequence[ProofCase],
    outputs: dict[str, str],
    *,
    gate_config: dict[str, Any] | None = None,
) -> CandidateMetrics:
    """Evaluate a candidate using deterministic gates plus held-out reference checks."""
    validate_output_coverage(cases, outputs)
    gate = OpenClawGovernanceGate()
    reason_counts: dict[str, int] = {}
    accept = caution = reject = 0
    gate_scores: list[float] = []
    expected_hits = 0
    forbidden_absent = 0
    realized_outputs: dict[str, str] = {}

    for index, case in enumerate(cases):
        output = outputs.get(case.case_id, "")
        realized_outputs[case.case_id] = output
        if not output.strip():
            reject += 1
            gate_scores.append(0.0)
            reason_counts["empty_output"] = reason_counts.get("empty_output", 0) + 1
        else:
            verdict = gate.evaluate(
                {"message": output, "prompt": case.prompt},
                GateContext(
                    run_id=f"openclaw-proof-{name}",
                    step_index=index,
                    prior_verdicts=[],
                    config=gate_config or {},
                ),
            )
            if verdict.decision == Decision.ACCEPT:
                accept += 1
                gate_scores.append(1.0)
            elif verdict.decision == Decision.CAUTION:
                caution += 1
                gate_scores.append(0.5)
            else:
                reject += 1
                gate_scores.append(0.0)
            for reason in verdict.reason_codes:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1

        lower_output = output.lower()
        if all(needle.lower() in lower_output for needle in case.expected_contains):
            expected_hits += 1
        if all(needle.lower() not in lower_output for needle in case.forbidden_contains):
            forbidden_absent += 1

    total = len(cases) or 1
    return CandidateMetrics(
        name=name,
        total=len(cases),
        accept_rate=accept / total,
        caution_rate=caution / total,
        reject_rate=reject / total,
        mean_gate_score=sum(gate_scores) / total,
        expected_contains_rate=expected_hits / total,
        forbidden_absent_rate=forbidden_absent / total,
        outputs=realized_outputs,
        reason_counts=reason_counts,
    )


def compare_candidates(
    baseline: CandidateMetrics,
    challenger: CandidateMetrics,
    *,
    temperature: float = 0.0,
    decoding: str = "greedy",
    min_gate_delta: float = 0.05,
) -> ImprovementProofReport:
    """Compare candidate metrics and decide if the adapter improved safely."""
    deltas = {
        "accept_rate": challenger.accept_rate - baseline.accept_rate,
        "mean_gate_score": challenger.mean_gate_score - baseline.mean_gate_score,
        "expected_contains_rate": challenger.expected_contains_rate
        - baseline.expected_contains_rate,
        "forbidden_absent_rate": challenger.forbidden_absent_rate - baseline.forbidden_absent_rate,
        "reject_rate": challenger.reject_rate - baseline.reject_rate,
    }
    precision_regression = (
        challenger.reject_rate > baseline.reject_rate
        or challenger.accept_rate < baseline.accept_rate
        or challenger.mean_gate_score < baseline.mean_gate_score
        or challenger.forbidden_absent_rate < baseline.forbidden_absent_rate
    )
    gate_non_regression = (
        challenger.reject_rate <= baseline.reject_rate
        and challenger.accept_rate >= baseline.accept_rate
        and challenger.mean_gate_score >= baseline.mean_gate_score
        and challenger.forbidden_absent_rate >= baseline.forbidden_absent_rate
    )
    challenger_clears_hard_gates = (
        challenger.reject_rate == 0.0
        and challenger.reason_counts.get("empty_output", 0) == 0
    )
    improved = (
        gate_non_regression
        and challenger_clears_hard_gates
        and (
            (
                deltas["mean_gate_score"] >= min_gate_delta
                and challenger.expected_contains_rate >= baseline.expected_contains_rate
            )
            or (
                deltas["expected_contains_rate"] > 0
                or deltas["forbidden_absent_rate"] > 0
            )
        )
    )
    return ImprovementProofReport(
        baseline=baseline,
        challenger=challenger,
        metric_deltas=deltas,
        improved=improved,
        precision_regression=precision_regression,
        promotion_allowed=improved and not precision_regression,
        temperature=temperature,
        decoding=decoding,
    )


def build_prompt(raw_prompt: str) -> str:
    """Format the proof prompt as a deterministic chat instruction."""
    return (
        "You are OpenClaw's Telegram response editor. Rewrite the draft into a "
        "concise, direct Telegram-ready message. Remove apology boilerplate, avoid "
        "wall-of-text paragraphs, and use short line breaks when listing actions.\n\n"
        f"{raw_prompt}"
    )


def generate_outputs(
    cases: Sequence[ProofCase],
    generate_one: Callable[[str], str],
) -> list[GeneratedOutput]:
    """Generate outputs for proof cases using an injected model callable."""
    return [GeneratedOutput(case.case_id, generate_one(build_prompt(case.prompt))) for case in cases]


def generate_outputs_with_unsloth(
    cases: Sequence[ProofCase],
    *,
    model_name: str,
    adapter_path: str | None = None,
    max_seq_length: int = 2048,
    max_new_tokens: int = 180,
    load_in_4bit: bool = False,
) -> list[GeneratedOutput]:
    """Generate deterministic outputs with local Qwen/Unsloth.

    Temperature is intentionally represented as greedy decoding (`do_sample=False`),
    which is the robust Transformers-compatible way to get temperature-0 behavior.
    """
    from unsloth import FastLanguageModel

    load_path = adapter_path or model_name
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=load_path,
        max_seq_length=max_seq_length,
        load_in_4bit=load_in_4bit,
    )
    FastLanguageModel.for_inference(model)
    if getattr(tokenizer, "pad_token", None) is None:
        tokenizer.pad_token = tokenizer.eos_token

    outputs: list[GeneratedOutput] = []
    for case in cases:
        prompt = build_prompt(case.prompt)
        messages = [{"role": "user", "content": prompt}]
        if hasattr(tokenizer, "apply_chat_template"):
            rendered = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
        else:
            rendered = prompt
        inputs = _tokenize_text_only(tokenizer, rendered).to(model.device)
        input_len = inputs["input_ids"].shape[-1]
        generated = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
        text = tokenizer.decode(generated[0][input_len:], skip_special_tokens=True).strip()
        outputs.append(GeneratedOutput(case.case_id, text))
    return outputs


def score_targets_with_unsloth(
    cases: Sequence[ProofCase],
    *,
    model_name: str,
    adapter_path: str | None = None,
    max_seq_length: int = 2048,
    load_in_4bit: bool = False,
    name: str = "candidate",
) -> TargetScore:
    """Score held-out target completions with teacher-forced NLL.

    This is the post-training proof that the adapter changed the model in the
    intended direction even before greedy decoding clears every gate.
    """
    import torch
    from unsloth import FastLanguageModel

    load_path = adapter_path or model_name
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=load_path,
        max_seq_length=max_seq_length,
        load_in_4bit=load_in_4bit,
    )
    FastLanguageModel.for_inference(model)
    if getattr(tokenizer, "pad_token", None) is None:
        tokenizer.pad_token = tokenizer.eos_token

    losses: dict[str, float] = {}
    for case in cases:
        target = case.target_completion or _target_from_expected(case)
        prompt_rendered = _render_chat_prompt(tokenizer, build_prompt(case.prompt))
        full_rendered = prompt_rendered + target
        prompt_inputs = _tokenize_text_only(tokenizer, prompt_rendered)
        inputs = _tokenize_text_only(tokenizer, full_rendered).to(model.device)
        labels = inputs["input_ids"].clone()
        prompt_len = prompt_inputs["input_ids"].shape[-1]
        labels[:, :prompt_len] = -100
        device_type = "cuda" if str(model.device).startswith("cuda") else "cpu"
        autocast_dtype = _autocast_dtype(torch, device_type)
        with (
            torch.inference_mode(),
            torch.autocast(
                device_type=device_type,
                dtype=autocast_dtype,
                enabled=autocast_dtype is not None,
            ),
        ):
            output = model(**inputs, labels=labels)
        losses[case.case_id] = float(output.loss.detach().cpu())

    mean_loss = sum(losses.values()) / (len(losses) or 1)
    return TargetScore(name=name, mean_loss=mean_loss, case_losses=losses)


def compare_target_scores(
    baseline: TargetScore,
    challenger: TargetScore,
    *,
    min_loss_delta: float = 0.01,
) -> TargetScoreReport:
    """Compare teacher-forced target losses."""
    loss_delta = baseline.mean_loss - challenger.mean_loss
    return TargetScoreReport(
        baseline=baseline,
        challenger=challenger,
        loss_delta=loss_delta,
        improved=loss_delta >= min_loss_delta,
        promotion_allowed=False,
    )


def _autocast_dtype(torch_module: Any, device_type: str) -> Any | None:
    """Choose the safest autocast dtype for target scoring on the current device."""
    if device_type != "cuda":
        return None
    cuda = getattr(torch_module, "cuda", None)
    if cuda is not None and cuda.is_bf16_supported():
        return torch_module.bfloat16
    return getattr(torch_module, "float16", None)


def _tokenize_text_only(tokenizer: Any, rendered: str) -> Any:
    """Tokenize text for both plain tokenizers and multimodal processors."""
    try:
        return tokenizer([rendered], return_tensors="pt")
    except ValueError as exc:
        # Qwen VL processors interpret the first positional argument as images.
        if "Incorrect image source" not in str(exc):
            raise
        return tokenizer(text=[rendered], images=None, videos=None, return_tensors="pt")


def _render_chat_prompt(tokenizer: Any, prompt: str) -> str:
    messages = [{"role": "user", "content": prompt}]
    if hasattr(tokenizer, "apply_chat_template"):
        return cast(
            str,
            tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            ),
        )
    return prompt


def _target_from_expected(case: ProofCase) -> str:
    if case.expected_contains:
        return "\n".join(case.expected_contains)
    raise ValueError(f"Proof case {case.case_id} needs target_completion or expected_contains")
