# Session: Pricing Strategy & CEO Review — 2026-05-01

## Context
YC deadline May 4th. Zero customer conversations. Branch: feat/skillify-loop.

## Starting Question
Gabriel proposed a pricing model: free explore/diagnose from existing traces → paid improvement (local models, fine-tuning, RLVR compute). Asked three questions:
1. How do we compete with people copying the loop with Claude/Codex?
2. How do we actually provide value for R&D/engineering domains?
3. How does the pricing model work?

## Initial Strategic Analysis (pre-CEO-review)

### Pricing Model
- Free tier as described ("explore and find errors") is what Langfuse already does for free
- Free tier must demonstrate something Langfuse structurally cannot: domain-specific gate evaluation that separates "safe to learn from" traces from "will poison your training data"
- Three tiers proposed: Free (domain gate scoring) → Govern (continuous enforcement) → Improve (local model replacement + training)

### Competitive Defense (ranked by defensibility)
1. Domain evaluator implementations (hardest to copy — actual domain physics)
2. Calibrated failure corpora (compounds over time)
3. Governed training traces (network effect — structurally better than LLM-as-judge)
4. Evidence-delta ledgers (regulatory-grade trust infrastructure)

### Value for R&D/Engineering
- Catch unsafe promotions before they cost money
- Convert rejections into governed next experiments (not dead ends)
- Training signal structurally better than LLM-as-judge
- "Before Detrix, you couldn't deploy this agent. After Detrix, you have proof."

## CEO Review (/plan-ceo-review) — Decisions

### D1: Pricing Focus
**Chosen: C) Both — dual narrative.** Services revenue now + freemium product vision.

### D2: Packaging Approach
**Chosen: C) Shadow-observer-first.** Free trace scoring → paid everything. (Both Claude and Codex later recommended incident-response-first instead. Gabriel held conviction on shadow observer.)

### D3: Review Mode
**Chosen: A) Selective expansion.** Stress-test + surface expansion opportunities.

### D4: Trace Triage Report as free tier deliverable
**ACCEPTED.** Script runs gates on traces, generates shareable markdown report. Ships in hours.

### D5: Simplify paid tier to "Governed Training Signal" only
**REJECTED.** Gabriel wants full stack: improve + replace API models + compute for training.

### D6: Open-source runtime (Apache 2.0)
**ACCEPTED.** Open-source GovernanceGate/VerdictContract. Charge for domain packs. Announced intent — actual publication post-YC.

### D7: Customization model
**Chosen: KLA model.** Free generic gates + $1K+ founding pilot / $5K+ standard domain engagements producing reusable packs.

Research agents found: KLA does $2.68B/yr in recipe services. Snorkel raised $100M at $1.3B on domain-specific evaluation. No competitor has a gate factory. Entry pricing for domain-specific eval: $50-60K/yr (Snorkel).

Gabriel's response: "Our dataset is basically the gates and reliability we build for these domain specific agents."

### D8: Free tier differentiation
**Chosen: A) Training eligibility classification.** Report classifies traces as pass / output-quality reject / input-quality reject. Nobody else does this.

### D9: Audience framing
**Chosen: A) Dual framing.** Deployment reliability + training eligibility. Same VerdictContract taxonomy, two interpretations for two audiences.

### D10: Data handling
**Chosen: D) All three as tiers.** Local (free), managed+NDA (standard paid), dedicated infra (enterprise).

### D11: Outside Voice (Codex)
Ran. 10 findings. Key tensions:

### D12: GTM sequence (cross-model tension)
Both Claude and Codex recommended incident-response-first. Gabriel chose to keep shadow-observer-first. Reasoning: attaching to existing traces is lower friction than "send us a bad run."

Hybrid compromise: incident response outbound NOW, shadow observer as the product pitch in YC app.

## Codex Outside Voice — Full Findings
- Free tier generic gates don't prove the domain-physics claim
- "Ships in hours" is overloaded for Day 1-2 timeline
- Support-triage demo weakens the wedge (makes Detrix look generic) → ACCEPTED, removed
- Training eligibility is wrong lead for prospects not fine-tuning → partially addressed via dual framing
- Paid tier overstuffed at $5K for full stack → risk noted, user chose to keep bundled
- "Reusable domain pack" isn't automatic — data rights, consent missing
- Launch sequence sends too few messages vs sprint target
- No crisp conversion trigger → ACCEPTED: "we install the gate that catches this failure class"
- KLA analogy risks sounding like consulting dressed as platform
- Biggest miss: incident response is simpler and stronger GTM

## Research Findings: Competitive Pricing Landscape

| Company | Free Tier | Paid Entry | Custom Evals | Domain Depth |
|---------|-----------|------------|-------------|--------------|
| Langfuse | 50K units, 2 seats | $29/mo | Self-serve Python | None |
| Braintrust | 1M spans | $249/mo flat | Self-serve code scorers | None |
| Promptfoo | OSS unlimited | Free community | Self-serve YAML/Python | None |
| Confident AI | 2 seats, 5 runs/wk | $19.99/seat/mo | 50+ built-in + Python | None |
| Credo AI | None | $30K-$150K/yr | Consulting-heavy | Policy/compliance |
| Snorkel AI | None | $50-60K/yr | Self-serve + white-glove | Yes — labeling functions |

Pattern: generic platform for adoption, domain expertise as higher-margin tier. Nobody has a gate factory.

## Strategic Conversations

### On competitive defense
"The moat isn't the gates (code is copyable). The accumulated failure corpus, calibrated thresholds, and governed training traces per domain. Compounds with each customer."

### On the consulting trap
"The consulting trap is only a trap when the output dies in the commit history. When it becomes a domain pack, it's a subscription." KLA's custom recipes = $2.68B/yr because they compound.

### On which domain to lead with
- Materials science: strongest PROOF (6 gates, 16/16 ACCEPT precision). Academic-heavy prospects.
- Regulated agents (finance, healthcare, legal): most urgent PAIN, highest willingness to pay. Zero existing gates.
- Manufacturing: warmest PATH (ex-Tesla network). Only 2 contacts.
- Decision: "You don't need to pick one domain forever. You need to pick which 5 messages to send first."

### On the self-running agent thesis
"Governance-only is a feature, not a company. The improvement loop IS the product. Enterprise governance is the on-ramp, self-running agents are the highway."

### On what would make the thesis wrong
Three scenarios:
1. Domain-specific evaluation turns out not to matter (frontier models self-evaluate accurately)
2. Failure corpus doesn't transfer between customers (every engagement is bespoke)
3. Teams build their own gates and the barrier is lower than expected ("good enough" risk)

Counterargument: 47.6% have no evaluation at all. Detrix competes with the status quo of nothing, not with internal solutions.

### On the Steven Gao message
"We built a system that tells you which AI recommendations are safe to act on and which ones would have caused problems — before they hit the floor." 18 words.

## What Shipped

### Code
- `src/detrix/triage/gates.py` — OutputFormatGate, LatencyAnomalyGate, CostAnomalyGate
- `src/detrix/triage/report.py` — Trace Triage Report generator (dual framing: deployment + training)
- `src/detrix/cli/main.py` — `detrix triage` CLI command
- `tests/test_triage_report.py` — 9 tests, all passing
- `examples/axv2_sample_traces.jsonl` — 16 realistic AXV2 traces
- `examples/axv2_triage_report.md` — generated sample report (the sales artifact)

### Usage
```
detrix triage traces.jsonl -o report.md
```

### Docs
- `docs/outreach-plan-2026-05-01.md` — 22 targets, schedule, templates, conversion playbook
- `~/.gstack/projects/gabegraves-detrix-core/ceo-plans/2026-05-01-shadow-observer-pricing.md` — full CEO plan

## Customer Discovery Transfer

11 interviews from Nov-Dec 2025 (original Detrix product — data logging/knowledge graph). Three patterns transfer directly to the new governance product:

1. **Corrections don't feed back** (Ryan, Hyewon, Jackie) — "Users manually correct data mappings but corrections do not feed back into improving future mappings." Exact Detrix thesis.
2. **Trust requires traceability** (Jacob Feder, Jennifer Garland) — "If agents could provide transparent processing steps, confidence in their use would increase." Strict audit requirements at Argonne.
3. **Guardrails are urgent** (Ryan) — Cited $47K runaway agent cost. Used "guardrails" unprompted. "95% of AI projects fail to deliver expected ROI."

Additional transferable:
- Jacob's systematic vs stochastic error distinction → case for deterministic gates over LLM-as-judge
- Jackie: reliability + provenance are the differentiators, not AI capabilities
- Revanth: agents as judges, observability/traceability still nascent, competitive differentiation narrowing

## YC App — What to Write

For "What have you learned from talking to users?":

> We interviewed 11 people across materials science (GM, Sila Nano, Argonne National Lab, physics startups), ML infrastructure (hedge fund ML ops), and self-driving labs (University of Toronto SDL). Three patterns repeated:
>
> 1. Corrections don't feed back. Users catch agent mistakes but the fixes die in the commit history.
> 2. Trust requires traceability. Scientists and engineers won't act on AI outputs without domain-specific evidence.
> 3. Guardrails are urgent. One interviewee cited a $47K runaway agent cost from 11 days unmonitored.
>
> We're now the first user — AgentXRD_v2 is our own materials science pipeline. We've started outreach to teams in manufacturing, autonomous labs, and regulated workflows.

## Next Steps (as of end of session)
1. Send 5 warm messages to California founders (IndustrialMind, HumanLayer, Agentin, Lila Sciences)
2. Send 15-20 cold messages Saturday morning with sample report attached
3. Draft YC application sections Sunday
4. Submit Monday May 4th
