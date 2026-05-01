# Detrix Outreach Plan — Friday May 1, 2026

Status: active today only. YC deadline May 4th.

## Schedule

### 5 AM - 9 AM: Build the Weapon

Build the Trace Triage Report generator and one sample report before anyone is at their desk.

1. Build OutputFormatGate (generic gate, ~30 min)
2. Write report generator script: takes AXV2 traces, runs gates, outputs markdown classifying each trace as:
   - pass (SFT-positive, deployment-safe)
   - output-quality reject (agent was wrong — DPO-negative, deployment risk)
   - input-quality reject (bad data, not agent's fault — exclude from training)
3. Generate AXV2 sample report — this is the attachment for every cold message
4. RegressionGate (stretch — skip if report is already compelling)

Done when: one markdown report exists that a VP Engineering could read and understand in 2 minutes.

### 9 AM - 12 PM: Warm Network (5 messages)

Highest conversion. Casual tone. No pitch deck. Attach the sample report.

| # | Person | Company | Connection | Hook | Channel |
|---|--------|---------|------------|------|---------|
| 1 | Steven Gao | IndustrialMind.ai | ex-Tesla | Manufacturing AI process control — governing agent recommendations before they reach the factory floor | Direct message |
| 2 | Jeff Wang | IndustrialMind.ai | ex-Tesla | Same company, technical angle — making AI process-control outputs auditable and regression-tested | Direct message |
| 3 | Dexter Horthy | HumanLayer | YC batch | His human-approval layer is downstream; Detrix decides which outputs need human review upstream | YC community / GitHub |
| 4 | Sankeerth Rao Karingula | Agentin AI | YC batch | Trains agents to learn from failures — Detrix separates safe-to-learn-from vs training-poisonous traces | YC community |
| 5 | Rafael Gomez-Bombarelli | Lila Sciences | Materials science | $550M autonomous lab — needs to know when a hypothesis result is trustworthy vs confidently wrong | Public team page / email |

Warm message template:

> Hey [Name] — building governance infrastructure for AI agent outputs in [their domain]. We score traces and classify which outputs are trustworthy vs which will produce bad results if deployed or trained on.
>
> Attached a sample report from a materials science agent pipeline — takes 15 minutes to run on your traces. Worth a quick call?

### 12 PM - 2 PM: Cold Outreach Tier 1 (15-20 messages)

Highest pain signal, plausible contact route. Attach the sample report.

| # | Person | Company | Pain Signal | Outreach Angle | Channel | Priority |
|---|--------|---------|-------------|----------------|---------|----------|
| 1 | John Nay | Norm Ai | Regulatory AI agents — compliance workflows | Detrix scores traces against policy acceptance criteria before promotion | Public founder route | Send today |
| 2 | Judson Ivy | Ensemble Health Partners | HIPAA + agentic RCM | Governed trace audit for one denials workflow | Public company route | Send today |
| 3 | Dimitri Masin | Gradient Labs | Regulated finance support agents | Failure taxonomy + promotion gates before reaching customers | Public company route | Send today |
| 4 | Gabriel Stengel | Rogo | Finance AI analyst — accuracy is everything | Governed promotion: no regression before analysts trust a new workflow | Public company route | Send today |
| 5 | Jesse Zhang | Decagon | Evaluation engine for AI agents | Domain-specific gates on top of their existing eval infrastructure | Public LinkedIn / site | Send today |
| 6 | Deepak Singla | Fini | 2M+ monthly fintech support tickets | Audit-ready eval and regression evidence for risky agent changes | Public LinkedIn | Send today |
| 7 | Christian Munley | NVIDIA NeMo | Requested tool hallucination rate as training metric | Detrix turns tool hallucination + governance failures into training eligibility signals | GitHub issue #922 | Send today |
| 8 | Timothy Kassis | K-Dense | Scientific Agent Skills — chemistry, materials, lab automation | Post-hoc gates on scientific skill runs → validated training examples | Public email / GitHub | Send today |
| 9 | Ry Nduma | CrystaLyse.AI | Provenance-enforced materials agent with JSONL audit trails | Shared materials-agent provenance — scoring outputs against acceptance gates | GitHub / personal site | Send today |
| 10 | Mo Nasir | Altrina | Reliable browser automations that should not break or fail silently | Score SOP automation failures into replayable evals before agent updates ship | YC community | Send today |

Cold message template:

> Subject: Which of your agent traces are safe to learn from?
>
> [Name] — saw [specific pain signal]. We built something that scores agent traces and classifies them: which outputs are trustworthy, which are confidently wrong, and which will poison your training data if you fine-tune on them.
>
> Attached is a sample report from a materials science agent pipeline. Takes 15 minutes to run on your traces.
>
> Worth a 10-minute call this week?

### 2 PM - 5 PM: Follow Up + Materials Science Tier

Follow up on any morning responses. Send remaining messages to materials/scientific targets.

| # | Person | Company | Angle | Channel |
|---|--------|---------|-------|---------|
| 1 | Anubhav Jain | Berkeley Lab FORUM-AI | Materials governance feedback — turning reasoning/tool traces into physics-checked evidence | Public lab route |
| 2 | Jacob Wright | Castari | Layering governed outcome evidence on top of sandbox/observability infrastructure | YC community |
| 3 | Connor Shorten | Weaviate | Query-agent evals need workflow-specific acceptance evidence, not generic hallucination benchmarks | GitHub / public profile |

### Evening: Prep Saturday Batch

Draft messages for Mon-Tue tier prospects (higher-value but harder to reach):

- Munjal Shah, Hippocratic AI — healthcare agents with clinician safety checks
- Gabe Pereyra, Harvey — long-horizon legal agents with ethical-wall handling
- George Sivulka, Hebbia — finance/legal users needing model process visibility
- Imran Siddique, Microsoft — Agent Governance Toolkit practitioner feedback

## Conversion Playbook

When a prospect responds positively, the conversion sequence is:

1. **15-min discovery call:** What agent workflow? What goes wrong? How do they catch it today?
2. **Free Trace Triage Report:** Run their actual traces through gates. Deliver markdown report.
3. **Conversion trigger:** Report shows a class of failure → paid offer: "We install the gate that catches this failure class. $1K founding pilot, normally $5K."
4. **Founding pilot scope:** One workflow, one gate set, one report, one next-action loop. Each engagement produces a reusable domain pack.

## Message Volume Targets

| Window | Target | Type |
|--------|--------|------|
| 9 AM - 12 PM | 5 | Warm network |
| 12 PM - 2 PM | 15-20 | Cold Tier 1 |
| 2 PM - 5 PM | 3-5 | Materials / follow-up |
| **Total today** | **23-30** | |
| Saturday | 5-10 | Mon-Tue tier (drafted Friday evening) |
| **Total before YC** | **28-40** | Sprint target: 25-40 |

## Assets Needed Before 9 AM

- [ ] OutputFormatGate implemented
- [ ] Trace Triage Report generator script (AXV2 traces → markdown)
- [ ] One sample report generated and reviewed
- [ ] Cold message template finalized with report attachment

## What NOT To Do Today

- Do not build the Langfuse connector — JSONL traces are enough for now
- Do not build RegressionGate unless you finish the other three items before 9 AM
- Do not open-source anything — announce the intent in the YC app, execute post-deadline
- Do not send messages without the sample report attached — the artifact IS the pitch
- Do not spend afternoon building instead of following up on morning responses
