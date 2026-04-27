# YC Demo Terminal Transcript - 2026-04-27

Command:

```bash
uv run detrix --data-dir /tmp/detrix-yc-demo-final/.detrix demo-yc --output-dir /tmp/detrix-yc-demo-final/out
```

Result:

```text
Detrix YC governance demo complete
Run ID: yc-demo-22e3013d
Audit DB: /tmp/detrix-yc-demo-final/.detrix/audit.db
Evidence DB: /tmp/detrix-yc-demo-final/.detrix/evidence.db
Artifact: /tmp/detrix-yc-demo-final/out/yc-demo-22e3013d.governance.json

Gate verdicts
- accept: ACCEPT via pii_detected, citations_required, confidence_threshold
- reject_pii: REJECT via pii_detected
- caution: CAUTION via pii_detected, citations_required, confidence_threshold
- request_more_data: REQUEST_MORE_DATA via pii_detected, citations_required, confidence_threshold

Terminal routes
- accept: route=ACCEPT rejection_type=-
- caution: route=CAUTION rejection_type=output_quality
- reject_pii: route=REJECT rejection_type=output_quality
- request_more_data: route=REQUEST_MORE_DATA rejection_type=input_quality

Training exports
- SFT rows: 1 -> /tmp/detrix-yc-demo-final/out/yc-demo-22e3013d.sft.jsonl
- DPO rows: 1 -> /tmp/detrix-yc-demo-final/out/yc-demo-22e3013d.dpo.jsonl
- GRPO rows: 1 -> /tmp/detrix-yc-demo-final/out/yc-demo-22e3013d.grpo.jsonl

SFT guard
- accepted: eligible
- caution: blocked (Cannot use rejected trace for SFT)
- rejected: blocked (Cannot use rejected trace for SFT)
- request_more_data: blocked (Cannot use rejected trace for SFT)

Close line: Observability tells you what happened after you check. Detrix tells you what was safe while you weren't watching.
```
