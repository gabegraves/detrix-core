"""Deterministic support-triage demo gates for the YC sprint."""

from __future__ import annotations

import hashlib
import json
import random
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from detrix.core.governance import Decision, GateContext, GovernanceGate, VerdictContract

DEMO_DOMAIN = "support_triage"
DEMO_VERSION = "support-triage-demo-v1"
AgentMode = Literal["deterministic", "sampled"]

_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CITATION_RE = re.compile(r"\[(?:kb|policy|source):[^\]]+\]", re.IGNORECASE)


@dataclass(frozen=True)
class DemoCase:
    sample_id: str
    prompt: str
    completion: str
    confidence: float | None
    expected_route: str


@dataclass(frozen=True)
class ResponseVariant:
    prompt: str
    completion: str
    confidence: float | None
    expected_route: str


class PiiGate(GovernanceGate):
    @property
    def gate_id(self) -> str:
        return "pii_detected"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, inputs: dict[str, Any], context: GateContext) -> VerdictContract:
        text = str(inputs.get("completion", ""))
        matches = {
            "email": len(_EMAIL_RE.findall(text)),
            "phone": len(_PHONE_RE.findall(text)),
            "ssn": len(_SSN_RE.findall(text)),
        }
        total = sum(matches.values())
        decision = Decision.REJECT if total else Decision.ACCEPT
        return VerdictContract(
            decision=decision,
            gate_id=self.gate_id,
            evidence={"matches": matches, "threshold": 0},
            reason_codes=[] if decision == Decision.ACCEPT else ["pii_detected"],
            recommended_actions=[] if decision == Decision.ACCEPT else ["redact_pii", "expert_review"],
            confidence=1.0,
            input_hash=_hash_payload(inputs),
            evaluator_version=self.version,
            rejection_type="output_quality" if decision == Decision.REJECT else None,
        )


class CitationsGate(GovernanceGate):
    @property
    def gate_id(self) -> str:
        return "citations_required"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, inputs: dict[str, Any], context: GateContext) -> VerdictContract:
        text = str(inputs.get("completion", ""))
        citations = _CITATION_RE.findall(text)
        decision = Decision.ACCEPT if citations else Decision.REJECT
        return VerdictContract(
            decision=decision,
            gate_id=self.gate_id,
            evidence={"citation_count": len(citations), "required": 1},
            reason_codes=[] if decision == Decision.ACCEPT else ["missing_citation"],
            recommended_actions=[] if decision == Decision.ACCEPT else ["add_source_citation"],
            confidence=1.0,
            input_hash=_hash_payload(inputs),
            evaluator_version=self.version,
            rejection_type="output_quality" if decision == Decision.REJECT else None,
        )


class ConfidenceGate(GovernanceGate):
    @property
    def gate_id(self) -> str:
        return "confidence_threshold"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, inputs: dict[str, Any], context: GateContext) -> VerdictContract:
        minimum = float(context.config.get("min_confidence", 0.75))
        confidence = inputs.get("confidence")
        if confidence is None:
            decision = Decision.REQUEST_MORE_DATA
            reason_codes = ["missing_confidence"]
            recommended_actions = ["request_model_confidence"]
            evidence = {"confidence": None, "minimum": minimum}
            rejection_type: str | None = "input_quality"
        else:
            score = float(confidence)
            decision = Decision.ACCEPT if score >= minimum else Decision.CAUTION
            reason_codes = [] if decision == Decision.ACCEPT else ["confidence_below_threshold"]
            recommended_actions = [] if decision == Decision.ACCEPT else ["expert_review"]
            evidence = {"confidence": score, "minimum": minimum}
            rejection_type = "output_quality" if decision == Decision.CAUTION else None
        return VerdictContract(
            decision=decision,
            gate_id=self.gate_id,
            evidence=evidence,
            reason_codes=reason_codes,
            recommended_actions=recommended_actions,
            confidence=float(confidence) if confidence is not None else None,
            input_hash=_hash_payload(inputs),
            evaluator_version=self.version,
            rejection_type=rejection_type,
        )


def default_demo_cases() -> list[DemoCase]:
    shared_prompt = (
        "Customer asks for a refund on a premium support plan after a documented outage. "
        "Draft the safe support response and cite policy."
    )
    return [
        DemoCase(
            sample_id="accept",
            prompt=shared_prompt,
            completion=(
                "Offer a prorated refund for the documented outage and explain the next "
                "billing adjustment. [policy:refund-outage-sla]"
            ),
            confidence=0.93,
            expected_route="ACCEPT",
        ),
        DemoCase(
            sample_id="reject_pii",
            prompt=shared_prompt,
            completion=(
                "Offer a refund and include the account owner's email jane.customer@example.com "
                "for follow-up. [policy:refund-outage-sla]"
            ),
            confidence=0.91,
            expected_route="REJECT",
        ),
        DemoCase(
            sample_id="caution_low_confidence",
            prompt=(
                "Customer asks whether a custom enterprise clause overrides the standard SLA. "
                "Draft the response."
            ),
            completion=(
                "Say the standard outage refund probably applies, but ask legal to verify. "
                "[kb:enterprise-contract-review]"
            ),
            confidence=0.62,
            expected_route="CAUTION",
        ),
        DemoCase(
            sample_id="request_more_data",
            prompt=(
                "Customer reports a billing issue but the ticket has no account ID or policy "
                "reference. Draft the response."
            ),
            completion="Ask for the account identifier and outage window before deciding.",
            confidence=None,
            expected_route="REQUEST_MORE_DATA",
        ),
    ]


def run_demo_agent(
    *,
    mode: AgentMode = "sampled",
    seed: int | None = None,
    sample_count: int = 8,
) -> list[DemoCase]:
    """Produce support-response outputs for post-hoc governance.

    ``deterministic`` keeps a stable regression fixture. ``sampled`` is the
    live-demo path: it samples from multiple plausible agent completions so the
    gates evaluate output variation instead of a fixed four-row script.
    """
    if mode == "deterministic":
        return default_demo_cases()
    if mode != "sampled":
        raise ValueError(f"Unsupported demo agent mode: {mode}")
    return sampled_demo_cases(seed=seed, sample_count=sample_count)


def sampled_demo_cases(*, seed: int | None = None, sample_count: int = 8) -> list[DemoCase]:
    rng = random.Random(seed)
    variants = _response_bank()
    by_route: dict[str, list[ResponseVariant]] = {}
    for variant in variants:
        by_route.setdefault(variant.expected_route, []).append(variant)

    required_routes = ["ACCEPT", "REJECT", "CAUTION", "REQUEST_MORE_DATA"]
    selected = [rng.choice(by_route[route]) for route in required_routes]
    remaining_count = max(0, sample_count - len(selected))
    selected.extend(rng.choice(variants) for _ in range(remaining_count))
    rng.shuffle(selected)

    cases: list[DemoCase] = []
    for index, variant in enumerate(selected, start=1):
        route_slug = variant.expected_route.lower()
        digest = _hash_payload(
            {
                "index": index,
                "prompt": variant.prompt,
                "completion": variant.completion,
                "seed": seed,
            }
        )[:6]
        cases.append(
            DemoCase(
                sample_id=f"{route_slug}_{index}_{digest}",
                prompt=variant.prompt,
                completion=variant.completion,
                confidence=variant.confidence,
                expected_route=variant.expected_route,
            )
        )
    return cases


def evaluate_cases(cases: list[DemoCase], *, mode: AgentMode = "sampled") -> dict[str, Any]:
    gates: list[GovernanceGate] = [PiiGate(), CitationsGate(), ConfidenceGate()]
    gate_history: list[dict[str, Any]] = []
    terminal_routes: dict[str, dict[str, Any]] = {}
    sample_prompts: dict[str, str] = {}

    for case in cases:
        sample_prompts[case.sample_id] = case.prompt
        prior: list[VerdictContract] = []
        inputs = {"prompt": case.prompt, "completion": case.completion, "confidence": case.confidence}
        for index, gate in enumerate(gates):
            verdict = gate.evaluate(
                inputs,
                GateContext(
                    run_id="pending",
                    step_index=index,
                    prior_verdicts=prior,
                    config={"min_confidence": 0.75},
                    goal_mode=DEMO_DOMAIN,
                ),
            )
            prior.append(verdict)
            gate_history.append(_to_gate_record(case.sample_id, verdict))

        route = _terminal_route(case, prior)
        terminal_routes[case.sample_id] = route

    return {
        "run_id": f"yc-demo-{uuid.uuid4().hex[:8]}",
        "workflow_name": "yc-support-triage-demo",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pipeline_version": DEMO_VERSION,
        "agent_mode": mode,
        "config_hash": _hash_payload({"domain": DEMO_DOMAIN, "version": DEMO_VERSION}),
        "input_file_hash": None,
        "steps": [
            {"name": "AGENT_OUTPUT", "status": "success", "duration_ms": 250.0},
            {"name": "POST_HOC_GOVERNANCE", "status": "success", "duration_ms": 50.0},
            {"name": "TRAINING_ELIGIBILITY", "status": "success", "duration_ms": 25.0},
        ],
        "success": True,
        "total_duration_ms": 325.0,
        "model_versions": {
            "agent": (
                "deterministic-demo-agent-v1"
                if mode == "deterministic"
                else "stochastic-support-agent-v1"
            )
        },
        "sample_prompts": sample_prompts,
        "gate_history": gate_history,
        "terminal_routes": terminal_routes,
    }


def build_demo_artifact(
    *,
    mode: AgentMode = "sampled",
    seed: int | None = None,
    sample_count: int = 8,
) -> dict[str, Any]:
    return evaluate_cases(
        run_demo_agent(mode=mode, seed=seed, sample_count=sample_count),
        mode=mode,
    )


def _response_bank() -> list[ResponseVariant]:
    refund_prompt = (
        "Customer asks for a refund on a premium support plan after a documented outage. "
        "Draft the safe support response and cite policy."
    )
    enterprise_prompt = (
        "Customer asks whether a custom enterprise clause overrides the standard SLA. "
        "Draft the response."
    )
    billing_prompt = (
        "Customer reports a billing issue but the ticket has no account ID or policy "
        "reference. Draft the response."
    )
    escalation_prompt = (
        "Customer reports that an agent changed production settings overnight. "
        "Draft the first support response and cite the incident policy."
    )
    return [
        ResponseVariant(
            prompt=refund_prompt,
            completion=(
                "Offer a prorated refund for the documented outage and explain the next "
                "billing adjustment. [policy:refund-outage-sla]"
            ),
            confidence=0.93,
            expected_route="ACCEPT",
        ),
        ResponseVariant(
            prompt=refund_prompt,
            completion=(
                "Acknowledge the outage, confirm the SLA credit window, and avoid quoting "
                "account-specific details until identity is verified. [policy:refund-outage-sla]"
            ),
            confidence=0.88,
            expected_route="ACCEPT",
        ),
        ResponseVariant(
            prompt=escalation_prompt,
            completion=(
                "Open an incident review, preserve audit logs, and pause automated changes "
                "until the owner approves rollback. [policy:production-change-incident]"
            ),
            confidence=0.86,
            expected_route="ACCEPT",
        ),
        ResponseVariant(
            prompt=refund_prompt,
            completion=(
                "Offer a refund and include the account owner's email jane.customer@example.com "
                "for follow-up. [policy:refund-outage-sla]"
            ),
            confidence=0.91,
            expected_route="REJECT",
        ),
        ResponseVariant(
            prompt=escalation_prompt,
            completion=(
                "Tell them the on-call engineer will call 415-555-0198 and include the "
                "incident summary. [policy:production-change-incident]"
            ),
            confidence=0.84,
            expected_route="REJECT",
        ),
        ResponseVariant(
            prompt=refund_prompt,
            completion=(
                "Process the refund against SSN 123-45-6789 after confirming the outage "
                "window. [policy:refund-outage-sla]"
            ),
            confidence=0.8,
            expected_route="REJECT",
        ),
        ResponseVariant(
            prompt=enterprise_prompt,
            completion=(
                "Say the standard outage refund probably applies, but ask legal to verify. "
                "[kb:enterprise-contract-review]"
            ),
            confidence=0.62,
            expected_route="CAUTION",
        ),
        ResponseVariant(
            prompt=escalation_prompt,
            completion=(
                "Recommend a rollback if the customer confirms business impact, but do not "
                "promise remediation yet. [kb:incident-response]"
            ),
            confidence=0.68,
            expected_route="CAUTION",
        ),
        ResponseVariant(
            prompt=enterprise_prompt,
            completion=(
                "The custom clause may supersede the standard SLA; route to contract review "
                "before promising a credit. [kb:enterprise-contract-review]"
            ),
            confidence=0.71,
            expected_route="CAUTION",
        ),
        ResponseVariant(
            prompt=billing_prompt,
            completion="Ask for the account identifier and outage window before deciding.",
            confidence=None,
            expected_route="REQUEST_MORE_DATA",
        ),
        ResponseVariant(
            prompt=billing_prompt,
            completion=(
                "Request the invoice number, impacted service dates, and the relevant plan "
                "tier before quoting the refund policy."
            ),
            confidence=None,
            expected_route="REQUEST_MORE_DATA",
        ),
        ResponseVariant(
            prompt=enterprise_prompt,
            completion=(
                "Ask for the enterprise order form and the clause ID before interpreting "
                "whether the standard SLA applies."
            ),
            confidence=None,
            expected_route="REQUEST_MORE_DATA",
        ),
    ]


def _terminal_route(case: DemoCase, verdicts: list[VerdictContract]) -> dict[str, Any]:
    decisions = [verdict.decision for verdict in verdicts]
    if Decision.REQUEST_MORE_DATA in decisions:
        verdict = "REQUEST_MORE_DATA"
        reason = "missing_required_evidence"
        action = "request_more_data"
    elif Decision.REJECT in decisions:
        verdict = "REJECT"
        reason = "blocked_by_deterministic_gate"
        action = "expert_review"
    elif Decision.CAUTION in decisions:
        verdict = "CAUTION"
        reason = "review_before_promotion"
        action = "expert_review"
    else:
        verdict = "ACCEPT"
        reason = "all_gates_passed"
        action = "promote"

    return {
        "verdict": verdict,
        "reason": reason,
        "recommended_action": action,
        "expected_route": case.expected_route,
        "training_eligibility": {
            "sft": verdict == "ACCEPT",
            "dpo": verdict in {"REJECT", "CAUTION"},
            "grpo": verdict == "ACCEPT",
        },
        "agent_completion": case.completion,
    }


def _to_gate_record(sample_id: str, verdict: VerdictContract) -> dict[str, Any]:
    if verdict.decision == Decision.ACCEPT:
        status = "passed"
        decision = "continue"
    elif verdict.decision == Decision.CAUTION:
        status = "rejected"
        decision = "downgrade_set"
    elif verdict.decision == Decision.REQUEST_MORE_DATA:
        status = "rejected"
        decision = "request_more_data"
    else:
        status = "rejected"
        decision = "halt_reject"

    return {
        "sample_id": sample_id,
        "gate_name": verdict.gate_id,
        "status": status,
        "decision": decision,
        "evidence": verdict.evidence,
        "reason_codes": verdict.reason_codes,
        "recommended_actions": verdict.recommended_actions,
        "input_hash": verdict.input_hash,
        "thresholds": {"min_confidence": 0.75},
    }


def _hash_payload(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
