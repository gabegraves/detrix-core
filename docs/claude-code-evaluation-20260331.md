# Evaluation: `nirholas/claude-code` for Detrix

Date: 2026-03-31
Source repo: `https://github.com/nirholas/claude-code`
Cloned commit: `c2357be81ef78536a09a63c2d3ffe6ea14bdb6d3`
Isolated clone path used for inspection: `/tmp/claude-code-scan-0pccsA/repo`
Bead: `detrix-core-s5v`

## Bottom line

This repository is useful as a **research artifact**, not as a code source.

Reason:
- The repo explicitly describes itself as leaked Claude Code source.
- `package.json` identifies it as `"0.0.0-leaked"` and "Not an official release."
- `LICENSE` says `UNLICENSED — NOT FOR REDISTRIBUTION` and warns it is proprietary Anthropic source.

For Detrix, that means:
- We should **not copy code** from this repository into Detrix.
- We can still extract **architecture ideas**, **control-plane patterns**, and **threat models** from it.
- Where a pattern is strong, we should reimplement it from first principles or from clean-room public sources.

## Malware / suspicious-content scan

### Method

Static-only inspection. I did not run the repo's install/build/start scripts.

Checks performed:
- shallow clone into an isolated `/tmp` directory
- executable file inventory
- grep sweep for suspicious patterns:
  - `curl|bash`, `wget|sh`, encoded PowerShell, `eval`, `new Function`
  - `child_process`, `subprocess`, base64 decode paths, shell wrappers
  - hardcoded secret patterns
- manual review of high-risk files:
  - `scripts/install.sh`
  - `gitpretty-apply.sh`
  - `docker/entrypoint.sh`
  - `.github/workflows/*.yml`
  - `web/app/api/exec/route.ts`
  - `src/server/security/command-sandbox.ts`
  - `src/server/api/services/exec-service.ts`
  - `src/server/api/routes/mcp.ts`

Environment note:
- `clamscan`, `yara`, and `semgrep` were not installed in this environment, so the scan was heuristic/static rather than AV-backed.

### Findings

No obvious malware payloads were found.

I did find several **high-risk execution surfaces**, which are expected for a coding-agent product but mean the repo should not be trusted or run casually:
- remote installer script that downloads files and starts Docker: `scripts/install.sh`
- server-side command execution endpoint: `web/app/api/exec/route.ts`
- shell-based execution service using `spawn("sh", ["-c", ...])`: `src/server/api/services/exec-service.ts`
- MCP server test route that shells out with `execSync`: `src/server/api/routes/mcp.ts`
- Docker entrypoint that forwards API keys into spawned processes: `docker/entrypoint.sh`

There were no hardcoded live credentials in the inspected content. Secret-like matches were examples, placeholders, validators, or secret-scanning code.

### Security conclusion

My current assessment is:
- **No immediate malware indicators**
- **Medium operational risk if executed**
- **High legal/provenance risk**

## What is actually useful for Detrix

### 1. Governance and permissioning patterns

Strong fit for Detrix:
- centralized permission modes
- explicit allowlist + denylist execution policy
- path sandboxing for file operations
- structured audit logging with secret scrubbing
- per-endpoint or per-action rate limiting

Relevant files:
- `src/server/security/command-sandbox.ts`
- `src/server/security/audit-log.ts`
- `src/server/security/rate-limiter.ts`
- `web/app/api/fs/*`
- `docs/subsystems.md` permission section

Why it matters for Detrix:
- Detrix is supposed to be a governance runtime, not just an orchestration wrapper.
- These patterns map directly to "observe, enforce, audit" control planes around agent actions.
- For hosted or multi-tenant Detrix later, this becomes core product infrastructure.

Detrix action:
- Reimplement a Python-native `ExecutionPolicy` layer:
  - allowlists
  - deny regexes
  - env scrubbing
  - cwd sandboxing
  - structured audit events
  - rate limits

### 2. Worktree and isolated-session patterns

Strong fit for agent-as-FDE and future Detrix operator tooling:
- isolated git worktrees per parallel agent/session
- slug validation to prevent path traversal
- cleanup lifecycle for ephemeral workspaces
- resume/reconnect logic for long-running sessions

Relevant files:
- `src/utils/worktree.ts`
- `docs/subsystems.md` coordinator section
- `docs/bridge.md`

Why it matters for Detrix:
- Detrix will likely need safe isolation for parallel improvement/eval jobs, adjudication agents, and overnight experiment lanes.
- Worktree/session isolation is especially relevant when multiple agents modify the same customer codebase or benchmark harness.

Detrix action:
- Borrow the pattern, not the code.
- Add a Detrix job-isolation design covering:
  - workspace isolation
  - branch naming
  - cleanup guarantees
  - traceability from job to git state

### 3. Skills/plugins/domain-pack shape

Conceptual fit:
- markdown/frontmatter-driven skill loading
- plugin discovery and constrained extension points
- MCP-backed skill generation

Relevant files:
- `src/skills/loadSkillsDir.ts`
- `docs/subsystems.md` skill + plugin sections
- `.mcp.json`

Why it matters for Detrix:
- Detrix needs **domain packs** and likely **evaluation packs**.
- This repo shows a practical way to represent composable agent behaviors as declarative files with metadata, tools, model preferences, and scope controls.

Detrix action:
- Define Detrix domain packs as clean-room public schemas:
  - domain metadata
  - evaluator registry
  - governance gates
  - prompt packs
  - memory policies
  - training-data extractors

### 4. Memory layering and secret-aware sync

Partial fit:
- layered memory scopes
- explicit team/shared memory
- client-side secret scanning before sync

Relevant files:
- `docs/subsystems.md` memory section
- `src/services/teamMemorySync/secretScanner.ts`

Why it matters for Detrix:
- Detrix’s differentiation depends on persistent memory and overnight improvement from scored traces.
- The memory hierarchy here is more human-instruction-centric than Detrix needs, but the operational lessons are useful:
  - memory scopes must be explicit
  - shared memory needs secret scanning
  - memory growth needs cleanup/versioning

Detrix action:
- Keep Detrix memory centered on run artifacts and scored traces, not markdown instruction files.
- Add a secret-scanning gate before syncing cross-tenant or team memory.
- Prefer direct use of public secret-scanning sources such as gitleaks rules, not this implementation.

### 5. Multi-agent coordinator patterns

Relevant, but not Phase 1 critical.

Relevant files:
- `docs/subsystems.md` coordinator section
- `src/coordinator/`
- task references in `docs/tools.md`

Why it matters for Detrix:
- Useful for operator tooling, agent teams, and future autonomous improvement loops.
- Less relevant to the immediate AgentXRD-first wedge than governance, scoring, provenance, and promotion.

Detrix action:
- Treat as roadmap inspiration, not immediate build input.

## What not to use for Detrix

### 1. Any source code directly

Do not port or adapt implementation from this repo.

Reason:
- explicit unlicensed proprietary/leaked status
- high contamination risk for a commercial product

### 2. Product framing

This repo is a terminal coding agent and companion web/server system.

Detrix should not drift toward:
- generic CLI assistant scope
- web terminal hosting
- IDE bridge work as a core identity
- plugin marketplace before governance/scoring are strong

Those are adjacent product surfaces, not the Detrix wedge.

### 3. The shell exec endpoints as written

There are useful ideas here, but some surfaces are too permissive or too UI-product-specific:
- `web/app/api/exec/route.ts` permits `sh` and `bash` in allowlists and has an unrestricted mode toggle
- `src/server/api/services/exec-service.ts` shells via `sh -c`
- `src/server/api/routes/mcp.ts` builds test commands with string concatenation into `execSync`

For Detrix, if we expose execution:
- use `execve`/`execFile`-style invocation only
- avoid shell interpolation
- bind every job to an auditable policy object
- isolate execution by runtime/container/workdir identity

## Recommended Detrix takeaways

### Safe to adopt as ideas

1. Governance policy as a first-class runtime subsystem
2. Structured audit logs with secret scrubbing
3. Rate-limited execution and control-plane endpoints
4. Worktree/job isolation for parallel agent execution
5. Declarative pack loading for skills/plugins/domain packs
6. Secret scanning before shared-memory sync

### Should be clean-room reimplemented

1. command sandbox
2. permission rule engine
3. audit logger
4. rate limiter
5. worktree isolation helper
6. domain-pack loader

### Not worth pulling into Phase 1

1. web terminal surfaces
2. IDE bridge architecture
3. plugin marketplace
4. generic CLI UX details
5. voice, browser, or broad consumer-assistant features

## Recommended next steps for Detrix

1. Build a clean-room `detrix.execution.policy` module inspired by the governance patterns here.
2. Add structured audit events for every gate decision, evaluator run, promotion decision, and memory write.
3. Write a small design note for isolated improvement/eval workspaces using git worktrees or disposable dirs.
4. Define a `domain-pack.yaml` or Pydantic schema instead of ad hoc pack wiring.
5. Add secret scanning before any future shared-memory or trace-export sync path.

## Final judgment

Use this repository as:
- architecture inspiration
- threat-model input
- UX and control-plane reference

Do not use it as:
- vendored code
- copy-paste source
- dependency source
- licensing-safe implementation material

The highest-value takeaway for Detrix is not "Claude Code internals." It is the reminder that **good agent products are built around control planes**: permissions, sandboxes, audit logs, memory scopes, isolation, and extension boundaries. That aligns with Detrix’s actual moat.
