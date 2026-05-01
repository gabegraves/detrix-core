# YC SDL Narrative + Market Research — 2026-05-01

Status: active strategic document. Synthesized from three parallel research agents covering SDL governance competitors, agent governance market signals, and SDL community pain signals.

## Revised YC Narrative

**One-liner:** Detrix is the quality inspector for self-driving labs — governance gates that catch what autonomous experiments get wrong before bad data compounds.

**The problem (with evidence):** The most prominent autonomous lab in the world published 71% success in Nature. A peer-reviewed reanalysis found zero new materials were actually discovered — the automated XRD analysis was, quote, "completely novice human level." This isn't hypothetical. 71% of SDL studies report no precision data. ~15 open-source SDL platforms exist. None have output quality gates.

**Why this matters now:** $850M+ is flowing into SDL (Periodic Labs alone raised $300M from a16z, Nvidia, DST, Bezos, Jeff Dean). Autonomous labs are being built. Governance infrastructure is not. The A-Lab incident is the canary — every lab running autonomous experiments without post-hoc validation is one reanalysis away from the same result.

**What Detrix does:** Post-hoc governance gates that evaluate every autonomous experiment output against domain physics. Did the Rietveld refinement converge? Is the phase identification consistent with known crystallography? Is the synthesis yield physically plausible? Gates that fail trigger governed next actions — retry, request human review, or flag for more data — instead of silently feeding wrong results into the next iteration.

**The self-improvement loop (differentiator):** Failed experiments don't just get flagged — they get converted into governed training data. The agent that failed a gate yesterday performs better tomorrow. No one else is closing this loop as a product. NeoCognition raised $40M for "agents that learn" but has no product. We have working code across two domains.

**Proof:** Two working domains — crystallography (AgentXRD, 6 gates, 16/16 precision) and quantitative trading (Parabola Hunter). Same GovernanceGate ABCs, same VerdictContract, different domain physics. The pattern transfers.

**Why us:** Materials science background, ex-Tesla. Built the XRD governance gates because I needed them — the exact gates that would have caught the A-Lab failure. Domain credibility in the field where SDL governance is most urgently needed.

**Market:** $850M+ in SDL funding with zero governance infrastructure. Security governance is crowded (Microsoft, Cisco). Output quality governance is wide open. KLA ($80B) is the precedent — quality inspection for chip fabs, not the fab itself.

**Ask:** $500K to ship governance packs for the 3 highest-value SDL domains (XRD/crystallography, synthesis optimization, spectroscopy), prove the self-improvement loop reduces failure rates 30%+, and build the gate factory for self-service onboarding.

---

## "Senior Engineer" Differentiation

The concern: "My senior engineer could build governance gates." Three layers of defensibility:

| Layer | Senior engineer can build? | What makes it hard |
|-------|---------------------------|-------------------|
| Gates + audit trail | Yes, in a week | Nothing — table stakes |
| Self-improvement loop | Maybe, in a quarter | Reward contamination, support-query versioning, holdout separation, governed promotion — subtle failure modes that bite after month 2 |
| Compounding failure corpus | No | Requires running in production across domains for months. Labeled failure taxonomies, calibration curves, evidence-delta ledgers compound over time |

The self-improvement loop is the near-term differentiator. The failure corpus is the long-term moat.

---

## Research: The A-Lab Story (Primary Demo Narrative)

A-Lab (Berkeley/LBNL) autonomous synthesis system (Szymanski et al., Nature 2023):
- Claimed 71% success synthesizing 41 of 58 novel inorganic materials
- Reanalysis by Palgrave (UCL) and Schoop (Princeton), published in PRX Energy 2024:
  - Zero new materials were actually discovered
  - Two-thirds of "successes" were ordered versions of already-known disordered compounds
  - Automated Rietveld refinement described as "very bad, very beginner, completely novice human level"
  - 35 of 36 samples classified as successes had one or more analysis errors

This is the published, peer-reviewed catastrophe that Detrix's AgentXRD gates would have caught.

Sources:
- Chemistry World: https://www.chemistryworld.com/news/new-analysis-raises-doubts-over-autonomous-labs-materials-discoveries/4018791.article
- PRX Energy: https://journals.aps.org/prxenergy/abstract/10.1103/PRXEnergy.3.011002
- Nature original: https://www.nature.com/articles/s41586-023-06734-w

---

## Research: SDL Governance Gap — Confirmed Open

### No one is building SDL governance

| Source | Finding |
|--------|---------|
| ~15 open-source SDL platforms (AlabOS, HELAO, IvoryOS) | Zero have post-hoc output scoring |
| Periodic Labs ($300M seed, a16z, Oct 2025) | Zero mention of governance in any coverage |
| Recursion, Ginkgo, Emerald Cloud Lab | Security governance only, no output quality gates |
| Nature Reviews Chemistry (Aspuru-Guzik, 2025) | Calls for governance; describes no system that does it |
| Royal Society review (2025) | 71% of SDL studies report no precision data; 65% lack algorithm comparison |
| SDL 2.0 paper (Materials Horizons, 2026) | Names absence of automated quality gates; validation remains ad-hoc |

### Academic governance papers (advocacy without implementation)

**"Steering towards safe SDLs" (Nature Reviews Chemistry, Aug 2025)** — Leong, Griesbach, Aspuru-Guzik et al. Proposes human-in-the-loop checkpoints, compartmentalization, real-time monitoring, kill switches. Gap confirmed: no existing SDL implements comprehensive automated output validation. The fact that Aspuru-Guzik co-authored a safety paper is itself a signal of community anxiety.

**Royal Society Open Science review (July 2025)** — "Most laboratories can only report calibration and benchmarking data" with "no standards for performing or enforcing reproducibility studies." No uniform detection, containment, or safe-shutdown mechanisms.

**SDL 2.0 (Materials Horizons, 2026)** — Six pillars for next-gen SDLs. Explicitly names: validation remains ad-hoc, human checkpoints are the only mechanism, "determination of when automation should defer to expert judgment remains unresolved."

**Performance Metrics paper (PMC, 2024)** — Proposed eight SDL metrics. None are standardized. No governance tooling exists to measure them.

### Pain signals from researchers

**"Adam" robot (Aberystwyth)** — Described as "brittle"; teams chose only robust chemistries to reduce unexpected failures. Practitioners work around unreliability rather than solving it.

**Aspuru-Guzik group (ACS Accounts of Chemical Research, 2022)** — Automated identification of unknown compounds is "incredibly challenging." Solid dispensing requires "substantial calibration and testing." "Few manufacturers develop their software to consider self-driving laboratories."

**Cost floor:** Commercial SDL systems exceed $1M in hardware. Even A-Lab's admitted 26% failure rate (before the reanalysis made it worse) translates to six-figure wasted runs per year.

### Forcing functions

- DOE "Shaping the Future of SDL" workshop (Denver, Nov 2024) — governance identified as critical unsolved problem
- FDA/EMA Joint Guiding Principles (Jan 2026) — regulatory pressure forming
- NIST AI Agent Standards Initiative (Jan-Feb 2026) — won't deliver until late 2026
- IP impasse: AI-generated inventions currently unpatentable. Governance + provenance records enable patentability claims — non-obvious value prop
- Databricks stat: 12x more projects reach production with governance+eval tools

---

## Research: Broader Agent Governance Market

### Competitive landscape — the naming opportunity

"Agent governance" is being captured by the security crowd. Detrix can own "agent output governance" or "agent reliability infrastructure" before the security framing swallows the term.

| Player | What they do | What they DON'T do |
|--------|-------------|-------------------|
| Microsoft Agent Governance Toolkit (Apr 2026) | Pre-execution policy (identity, access, sandboxing via OPA/Cedar). Answers "can this agent do this?" | Post-hoc output quality evaluation. Does NOT answer "did the agent do it well?" |
| Galileo → Cisco (acquired Apr 2026) | LLM-as-judge, 20+ generic metrics, real-time guardrailing | Deterministic domain-specific gates, physics verification |
| Braintrust ($36M) | Offline experiments, CI/CD regression loops | Domain-specific gate primitives, failure-to-training loop |
| Patronus AI (Series A) | LLM-based "generative simulators" for continuous improvement | Deterministic physics layer |
| Arize ($70M Series C) | Enterprise ML observability, monitoring | Output quality gates, governance enforcement |
| LangSmith / LangFuse | Tracing, observability | Governance enforcement of any kind |
| Databricks Agent Bricks | Data access control and lineage | Output quality evaluation |
| Fiddler | Compliance audit trails, regulated industries | Domain-specific correctness evidence |
| **Nobody** | — | **Failure → governed training data loop as a product** |
| **Nobody** | — | **Domain-specific deterministic gates packaged for enterprise** |

### Microsoft Agent Governance Toolkit — detailed assessment

Open-source, MIT-licensed, seven-package monorepo. Covers: pre-execution policy enforcement (sub-0.1ms via OPA/Cedar/YAML), zero-trust cryptographic identity, execution sandboxing, SLO/circuit-breaker reliability, compliance mapping (EU AI Act/HIPAA/SOC2). Claims "first to address all 10 OWASP Agentic AI Top 10."

**Critical confirmed gap:** The toolkit intercepts actions before execution. Zero mechanism for post-hoc output correctness evaluation, domain-specific quality gates, or failure-to-training-data closure. NOT a Detrix competitor — complementary layer that creates a named gap Detrix occupies.

Sources:
- https://opensource.microsoft.com/blog/2026/04/02/introducing-the-agent-governance-toolkit-open-source-runtime-security-for-ai-agents/
- https://github.com/microsoft/agent-governance-toolkit

### VC signals

- NeoCognition $40M seed (Apr 2026) — "agents that learn like humans." Research-stage, no product. Signals VC interest in self-improvement as a category.
- Cisco acquired Galileo (Apr 2026) — governance category being absorbed into security infrastructure
- a16z Big Ideas 2026 — agent governance framed as sorting factor between pilot and production
- Sequoia "2026: This is AGI" — governance as table stakes for enterprise adoption
- Databricks: 12x production deployment multiplier with governance+eval tools

### RLVR / self-improvement market

- DeepSeek R1, SWE-RL, AlphaEvolve — RLVR for coding/math with verifiable rewards (compiler, test suites)
- Pattern maps directly to Detrix's domain physics gates (Rietveld convergence, backtest reproducibility)
- No startup is productizing this for enterprise agent pipelines with mixed deterministic/advisory tiers
- MLAgentBench (Stanford) — 13-task benchmark with deterministic get_score() — confirms the recognized path but not packaged as product

### Acquisition pattern

Exit path for a point solution in this category is clearly M&A into security or cloud infrastructure players. Timing for Detrix to establish a vertical wedge: 12-18 months before the security layer absorbs the surface-level governance narrative.

---

## Cross-Domain Analogies

### KLA Corporation ($80B) — semiconductor process control

KLA provides post-process inspection and yield management for chip fabs — doesn't control what the fab makes, only scores outputs and governs which wafers proceed. SDL governance maps directly: high-capital instrument, expensive consumables, deterministic physics constraints (crystal structure, not circuit geometry), post-hoc scoring without constraining the agent's action space. KLA's moat is not measurement hardware — it's the failure taxonomy and process window database accumulated over decades.

### Aviation FOQA (Flight Operational Quality Assurance)

Airlines attach post-hoc telemetry analysis to every flight, scoring against deterministic safety envelopes. Failures trigger mandatory review. Pilots have full freedom during flight; scoring is invisible to them. SDL analog is exact: agent has full action freedom, Detrix scores post-hoc, failures feed training. Regulatory forcing function parallel: airlines adopted FOQA under FAA pressure. SDL regulatory pressure (FDA/EMA, DOE workshops) is the current analog.

### Pharmaceutical automation digital twins

Pre-SDL pharma automation uses simulation layers to validate instrument commands before execution — catching errors that would waste expensive reagents or damage equipment. The transition-admission pattern Detrix implements.

---

## Sources Index

### A-Lab / SDL Failures
- Chemistry World: A-Lab reanalysis — https://www.chemistryworld.com/news/new-analysis-raises-doubts-over-autonomous-labs-materials-discoveries/4018791.article
- PRX Energy: Palgrave/Schoop critique — https://journals.aps.org/prxenergy/abstract/10.1103/PRXEnergy.3.011002
- Nature: A-Lab original — https://www.nature.com/articles/s41586-023-06734-w
- ChemRxiv: Palgrave/Schoop preprint — https://chemrxiv.org/engage/chemrxiv/article-details/65957d949138d231611ad8f7

### SDL Governance Gap
- Nature Reviews Chemistry: Safe SDLs — https://www.nature.com/articles/s41570-025-00747-x
- Royal Society Open Science: SDL policy review — https://royalsocietypublishing.org/rsos/article/12/7/250646/235354/
- Royal Society PMC full text — https://pmc.ncbi.nlm.nih.gov/articles/PMC12368842/
- Materials Horizons: SDL 2.0 — https://pubs.rsc.org/en/content/articlehtml/2026/mh/d5mh01984b
- PMC: SDL Performance Metrics — https://pmc.ncbi.nlm.nih.gov/articles/PMC10866889/
- ACS: SDL Challenges — https://pmc.ncbi.nlm.nih.gov/articles/PMC9454899/

### Market / Competitors
- Microsoft Agent Governance Toolkit — https://opensource.microsoft.com/blog/2026/04/02/introducing-the-agent-governance-toolkit-open-source-runtime-security-for-ai-agents/
- Microsoft AGT GitHub — https://github.com/microsoft/agent-governance-toolkit
- Galileo Luna-2 — https://galileo.ai/blog/introducing-luna-2-purpose-built-models-for-reliable-ai-evaluations-guardrailing
- Cisco acquires Galileo — https://www.shashi.co/2026/04/cisco-acquires-galileo-when.html
- Databricks Enterprise AI Agent Trends — https://www.databricks.com/blog/enterprise-ai-agent-trends-top-use-cases-governance-evaluations-and-more
- Braintrust Agent Evaluation — https://www.braintrust.dev/articles/ai-agent-evaluation-framework
- CSA: AI Agent Governance Framework Gap — https://labs.cloudsecurityalliance.org/research/csa-research-note-ai-agent-governance-framework-gap-20260403/
- NeoCognition $40M — https://techcrunch.com/2026/04/21/ai-research-lab-neocognition-lands-40m-seed-to-build-agents-that-learn-like-humans/
- Periodic Labs $300M — https://techcrunch.com/2025/09/30/former-openai-and-deepmind-researchers-raise-whopping-300m-seed-to-automate-science/

### Scientific Agents / RLVR
- NVIDIA NeMo RL for scientific agents — https://developer.nvidia.com/blog/how-to-train-scientific-agents-with-reinforcement-learning/
- FutureHouse platform — https://techcrunch.com/2025/05/01/futurehouse-releases-ai-tools-it-claims-can-accelerate-science/
- POPPER hypothesis validation — https://arxiv.org/abs/2502.09858
- From AI for Science to Agentic Science survey — https://arxiv.org/html/2508.14111v1
- Nature Synthesis: reproducibility in automated chemistry — https://www.nature.com/articles/s44160-024-00649-8

### Regulatory / Policy
- OSTI: DOE SDL Workshop — https://www.osti.gov/biblio/2481197
- Built In: AI Agents in regulated industries — https://builtin.com/artificial-intelligence/ai-agent-trusted-regulated-industries
- Deterministic vs LLM evaluators study — https://dev.to/anshd_12/deterministic-vs-llm-evaluators-a-2026-technical-trade-off-study-11h

---

## 2026 Updates (Appended 2026-05-01)

### A-Lab Nature Correction — January 19, 2026

Nature issued a formal Author Correction (doi: s41586-025-09992-y). Key changes:
- "Novelty" language softened: materials described as new to the prediction platform, not new to science
- XRD re-analysis: 36 of 40 confirmed; 4 downgraded to "inconclusive from XRD alone"
- Ceder's defense (LinkedIn, Dec 2023): admitted MnAgO2 and Mg3Ni3MnO8 were not novel. Described low-quality Rietveld refinements as intentional — "our objective was to show what an autonomous lab can achieve, not the best human"
- Critics unsatisfied. Palgrave: correction "clarifies quite a few things" but doesn't address failure to predict real-world random particle arrangements. Schoop: "the advancement for humanity is very incremental"
- C&EN (Jan 2026) headline: "corrected, but some questions remain unanswered." No retraction.

**For Detrix narrative:** This is an active, unresolved 2026 controversy. The lab's own defense is "we didn't try to do good XRD analysis." Detrix's gates do exactly what they admitted they skipped.

Sources:
- Nature correction: https://www.nature.com/articles/s41586-025-09992-y
- C&EN coverage: https://cen.acs.org/research-integrity/Nature-robot-chemist-paper-corrected/104/web/2026/01
- Ceder LinkedIn post: https://www.linkedin.com/pulse/regarding-our-recent-a-lab-article-gerbrand-ceder-0sz6c

### Chemspeed + SciY SDL Platform — February 2026

Announced at SLAS2026 (Feb 9, 2026). First commercial vendor to bundle automation + governance infrastructure:
- SciY provides "AI-ready open data backbone" with vendor-agnostic FAIR data capture, ontology-driven semantics, audit trails, and traceable data for "critical decisions"
- Chemspeed provides "deterministic, reproducible execution"
- **Limitation:** Hardware-coupled (requires Chemspeed equipment). Not a standalone post-hoc governance layer for arbitrary agent traces. Detrix is decoupled from hardware.

Source: https://ir.bruker.com/press-releases/press-release-details/2026/Chemspeed-and-SciY-Announce-SelfDriving-Laboratory-Platform-Integrating-Automation-Analytics-and-AI-Orchestration/default.aspx

### Regulatory Developments — 2026

**NIST AI Agent Standards Initiative (Feb 17, 2026):**
First U.S. government program dedicated to autonomous AI agent standards. Three pillars: industry-led standards, community-led open protocols, foundational security/identity research. April 2026 listening sessions targeted healthcare and financial services. COSAiS project developing SP 800-53 control overlays for agent deployments. SDL governance tools that align with NIST standards get a compliance narrative for regulated customers.

Source: https://www.nist.gov/news-events/news/2026/02/announcing-ai-agent-standards-initiative-interoperable-and-secure

**FDA/EMA Joint Guidance (Jan 2026):**
"10 Guiding Principles of Good AI Practice in Drug Development." Key rule: "AI outputs are recommendations, not decisions." Human approval mandatory for any AI-driven action affecting product quality, safety, or efficacy. This is the regulatory forcing function for human-in-the-loop gates in pharma SDLs.

**FDA CSA Guidance (2025, effective 2026):**
Shifted validation from exhaustive documentation to risk-based critical thinking. Lowers compliance burden for SDL governance tools that demonstrate risk-based output scoring.

### SDL Market Status — 2026

**QPillars analysis (2026):** Vast majority of SDLs at Level 2 autonomy. "A handful reaching Level 3." No vendor offers post-hoc output governance as a standalone layer decoupled from hardware.

**Periodic Labs** (Fedus + Cubuk, ex-DeepMind, $300M): "easing into autonomy by automating pieces to ensure AI's proposed syntheses make sense." Human validation of AI proposals remains mandatory. No automated output governance.

**Lila Sciences**: Targeting mRNA therapeutics and catalysts. Still relies on human input to validate AI predictions as of 2026.

**Automata (LINQ platform)**: $45M Series C, Jan 2026, Danaher Ventures. 5 pharma customers. Lab workflow automation, not output governance.

**Zeon Systems (YC X25)**: Plain-English-to-robot-code interface. Stanford and UCSF labs. Execution layer only, no validation or governance.

**Acceleration Consortium**: CAN$200M federal grant, 50 autonomous robots. Aspuru-Guzik leading. Research focus, no commercial governance product. Profiled in Nature March 2026.

**Ginkgo Bioworks Cloud Lab**: 70+ instruments, targeting 100+ RACs by end of 2026. OpenAI collab achieved 40% cost reduction in cell-free protein synthesis. No public governance framework — human scientist review only.

**Strateos**: Pivoted from public cloud lab to private on-premises deployments — commercial signal that remote-access SDL faces trust/validation problems at scale.

### SDL Benchmarking — 2025-2026

**Benchmarking self-driving labs (Digital Discovery, Oct 2025)** — Adesiji, Wang, Kuo, Brown (Boston University). First systematic benchmarking framework. Two metrics: Acceleration Factor (AF, preferred) and Enhancement Factor (EF — varies over two orders of magnitude, definitions not standardized). Key finding: EF values are not comparable across SDLs. Noise sensitivity causes "drastic increases" in required experiments in complex parameter spaces. Stopping criteria at 10-20 experiments per dimension.

Source: https://pubs.rsc.org/en/content/articlehtml/2026/dd/d5dd00337g

### Additional 2026 Sources
- Nature: Inside the SDL revolution (Mar 2026) — https://www.nature.com/articles/d41586-026-00974-2
- Nature: Will robot labs replace biologists? (2026) — https://www.nature.com/articles/d41586-026-00453-8
- ChemRxiv: A foundational representation for an orchestrated lab (Jan 2026) — https://chemrxiv.org/doi/full/10.26434/chemrxiv-2026-v425m
- Zeon Systems YC profile — https://www.ycombinator.com/companies/zeon-systems

---

## SDL Governance — Peer-Reviewed Papers (Appended 2026-05-01)

### Key finding: no governance product exists in the literature

After exhaustive search, no commercial product or open-source project provides post-hoc output scoring, governed self-correction loops, or audit-trail-backed validation for SDL agent outputs. The peer-reviewed literature converges on naming the problem without solving it.

### Papers

**1. Benchmarking self-driving labs**
Adesiji, Wang, Kuo, Brown — Digital Discovery 5:14–27, 2026. DOI: 10.1039/D5DD00337G. Boston University.
First systematic SDL benchmarking framework. Defines Acceleration Factor (AF, median = 6) and Enhancement Factor (EF, peaks at 10-20 experiments/dimension). Key finding: EF values are not comparable across SDLs due to conflicting definitions. Reproducibility flagged as "a key challenge" — stochastic active learning campaigns produce different AF/EF values even in the same lab. Documents the need for governance without providing it.
Source: https://pubs.rsc.org/en/content/articlehtml/2026/dd/d5dd00337g

**2. Reproducibility in automated chemistry laboratories using computer science abstractions**
Canty, Abolhasani — Nature Synthesis 3:1327–1339, 2024. DOI: 10.1038/s44160-024-00649-8.
Translates CS abstractions (scenario-based programming, abstract data types, design patterns) into automated chemistry workflows to enforce reproducibility. Core argument: improper abstraction creates technical debt that breaks reproducibility. Closest peer-reviewed analog to a "governance layer for SDL workflows" — but targets workflow representation, not post-hoc output evaluation.
Source: https://www.semanticscholar.org/paper/Reproducibility-in-automated-chemistry-laboratories-Canty-Abolhasani/d2091472f7e6a5f56d81bb07d4f1a12bcda23abd

**3. A foundational representation for an orchestrated lab**
Gottstein, Blanc, Feng, Sutherland, García Carrillo — ChemRxiv preprint, Jan 16 2026. DOI: 10.26434/chemrxiv-2026-v425m. University of Toronto / Acceleration Consortium.
Proposes four nested constructs (primitives, unit operations, state-preserving flows, workflows) enabling "Lab as Code" — versioned, redeployable experimental specs analogous to Infrastructure as Code. Supports validation, safer parallelism, and inter-lab interoperability. No audit trail or post-hoc scoring mechanism. Not peer-reviewed yet. Structural analog to Detrix's GovernedTrajectory schema.
Source: https://www.cambridge.org/engage/chemrxiv/article-details/6966b95bff1c4bced4170241

**4. Toward self-driving laboratory 2.0 for chemistry and materials discovery**
Lee, Yoo, Jang, Park, Park, Han — Materials Horizons, advance article Mar 4 2026. DOI: 10.1039/D5MH01984B. KIST / Korea University.
Defines SDL 2.0 along six axes: interoperable, collaborative, generalizable, orchestrated, safe, creative. Documents that current systems "are unable to manage safety incidents without human oversight" and hazard detection is "typically limited to threshold-based alarms." Recommends version-controlled provenance-tracked digital recipes, XDL for protocol standardization, ChemTorrent for decentralized verification, graduated autonomy with experimental checkpoints. Names the right components but frames them as 2-5 year research goals, not deployable infrastructure.
Source: https://pubs.rsc.org/en/content/articlehtml/2026/mh/d5mh01984b

**5. Science acceleration and accessibility with self-driving labs**
Canty, Bennett, Brown, Buonassisi, Kalinin, Kitchin, Maruyama, Moore, Schrier, Seifrid, Sun, Vegge, Abolhasani — Nature Communications, Apr 24 2025. DOI: 10.1038/s41467-025-59231-1. 13-author multi-institution perspective.
States directly: "the current suite of tests and the integration of these controls into SDL workflows is lacking." Recommends SDL reports include calibrations, standards, and benchmarking data. Identifies trust as the primary adoption barrier. Names API opacity, fragmented ecosystems, and missing interoperability standards (SiLA 2, BlueSky) as structural blockers.
Source: https://pmc.ncbi.nlm.nih.gov/articles/PMC12022019/

**6. Steering towards safe self-driving laboratories**
Leong, Griesbach, Aspuru-Guzik et al. — Nature Reviews Chemistry, Aug 2025.
The field's main safety/governance position paper. Key quote: "AI technology is simply not yet sufficiently trustworthy to leave safety and security under its charge." Calls for human approval gates on all experimental plans and executable code. No system described that implements this.
Source: https://www.nature.com/articles/s41570-025-00747-x

**7. Autonomous self-driving laboratories: technology and policy review**
Tobias, Wahab — Royal Society Open Science 12(7):250646, July 2025. DOI: 10.1098/rsos.250646.
Most policy-oriented SDL review. Key quote: "failure to institute sensible, widespread policies and procedures risks obstruction of the entire SDL field in reaction to even one high-profile safety failure." Contains no discussion of audit trails, data provenance, or post-hoc output verification. Recommends human kill-switch, visual experiment summaries, strict code compartmentalization.
Source: https://royalsocietypublishing.org/rsos/article/12/7/250646/235354/

### Chemspeed / SciY — Detailed Assessment

SciY's "AI-ready open data backbone" (ZONTAL platform, Bruker division) claims FAIR data capture, ontology-driven semantics, 21 CFR Part 11 alignment, API-first architecture. Concrete governance claims are thin: "traceable, quantitative data required in critical decisions" is the strongest specific statement. Audit trail mechanics, provenance chain, and validation protocols not described in any public document. No peer-reviewed publications support the governance claims.

**Assessment:** Closest commercial analog to what Detrix does — but targets data management, not post-hoc output scoring or governed self-correction. Positioned at data infrastructure, not agent reliability.

Sources:
- Announcement: https://www.pharmiweb.com/press-release/2026-02-09/chemspeed-and-sciy-announce-self-driving-laboratory-platform-integrating-automation-analytics-and-a
- SciY product page: https://www.sciy.com/en/solutions/data-management/data-platform.html

### Related Standards and Protocols

**XDL (eXtensible Document Language):** Represents chemistry protocols as fully digital data objects. Structural analog to GovernedTrajectory schema. Solves the representation problem; does not solve the evaluation problem.

**ChemTorrent:** Decentralized protocol verification — labs execute and verify protocols before redistribution. Analogous to Detrix's holdout gate pattern (no promotion without independent verification) but for protocol distribution, not model training.

**SiLA 2 / BlueSky:** Instrument interoperability standards. Named in multiple papers as missing infrastructure. Not governance-specific.

**SAE Autonomy Levels → SDL Levels:** The field has directly adopted the SAE 0-5 framework. In regulated environments, SDLs will operate at Level 3-4 (human approval gates at critical decisions) for the foreseeable future. Governance infrastructure is the mechanism that defines what "human approval gate" means in practice.
