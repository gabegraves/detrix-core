# YC Demo Terminal Transcript - 2026-04-27

Command:

```bash
uv run detrix --data-dir /tmp/detrix-yc-demo-sampled/.detrix demo-yc --output-dir /tmp/detrix-yc-demo-sampled/out --seed 27
```

Result:

```text
Detrix YC demo: autonomous agent output -> post-hoc gates -> training signal
Run ID: yc-demo-fbac10b7
Agent mode: sampled
Artifact: /tmp/detrix-yc-demo-sampled/out/yc-demo-fbac10b7.governance.json

Gate verdicts
- ACCEPT outputs passed pii_detected, citations_required, and confidence_threshold
- REJECT outputs were stopped by pii_detected
- CAUTION output passed deterministic gates but failed confidence_threshold
- REQUEST_MORE_DATA output lacked citation/confidence evidence

Terminal routes
- 3 ACCEPT trajectories eligible for SFT and GRPO
- 1 CAUTION trajectory eligible for DPO only
- 3 REJECT trajectories eligible for DPO only
- 1 REQUEST_MORE_DATA trajectory blocked from training exports

Training exports
- SFT rows: 3 -> /tmp/detrix-yc-demo-sampled/out/yc-demo-fbac10b7.sft.jsonl
- DPO rows: 4 -> /tmp/detrix-yc-demo-sampled/out/yc-demo-fbac10b7.dpo.jsonl
- GRPO rows: 3 -> /tmp/detrix-yc-demo-sampled/out/yc-demo-fbac10b7.grpo.jsonl

SFT guard
- caution: blocked (Cannot use rejected trace for SFT)
- rejected: blocked (Cannot use rejected trace for SFT)
- request_more_data: blocked (Cannot use rejected trace for SFT)

Close line: Observability tells you what happened after you check. Detrix tells you what was safe while you weren't watching.
```
