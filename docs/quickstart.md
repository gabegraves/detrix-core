# Quickstart — Add reproducibility to your agent pipeline in 15 minutes

## 1. Install

```bash
pip install detrix
```

Or with uv:
```bash
uv add detrix
```

## 2. Define your pipeline

Create `pipeline.yaml`:

```yaml
name: my-pipeline
version: "1.0"
steps:
  - id: load
    function: my_steps.load_data
    outputs: [records, count]

  - id: process
    function: my_steps.process
    depends_on: [load]
    inputs:
      records: "$load.records"
    outputs: [results]
```

## 3. Write your step functions

Each step is a plain Python function that takes keyword args and returns a dict:

```python
# my_steps.py
def load_data(**kwargs):
    records = [{"id": 1, "value": 42}]
    return {"records": records, "count": len(records)}

def process(records, **kwargs):
    results = [{"id": r["id"], "doubled": r["value"] * 2} for r in records]
    return {"results": results}
```

## 4. Run it

```bash
detrix run pipeline.yaml -v
```

Output:
```
[detrix] RUN my-pipeline v1.0 [a1b2c3d4e5f6]
[detrix]   RUN     load (attempt 1)
[detrix]   RUN     process (attempt 1)
[detrix] DONE  my-pipeline [a1b2c3d4e5f6] 15ms

============================================================
Workflow:  my-pipeline v1.0
Run ID:   a1b2c3d4e5f6
Status:   SUCCESS
Duration: 15ms
============================================================
  [SUCCESS ] load                      8ms
  [SUCCESS ] process                   7ms
```

## 5. See your history

```bash
detrix history
```

```
RUN ID         WORKFLOW             STATUS     STARTED
-----------------------------------------------------------------
a1b2c3d4e5f6   my-pipeline          success    2024-01-15T10:30:00
```

## 6. Run it again — caching kicks in

```bash
detrix run pipeline.yaml -v
```

Same inputs → cached results → instant:
```
[detrix]   CACHED  load
[detrix]   CACHED  process
```

## 7. Change something, then diff

Modify your step logic, run again, then:

```bash
detrix diff a1b2c3d4e5f6 f6e5d4c3b2a1
```

```
Diff: a1b2c3d4e5f6 → f6e5d4c3b2a1
==================================================
  [CHANGED] Inputs hash differs
  [CHANGED] process: outputs, duration: +5ms
```

This is the "aha" moment — you can see exactly what changed between runs.

## 8. Export a run artifact

```bash
detrix export a1b2c3d4e5f6 -o run_artifact.json
```

The artifact is a portable JSON bundle containing everything about the run:
inputs, outputs, code revision, environment, step-by-step results.

## Next steps

- Add `retry` config to flaky steps
- Use `depends_on` to build complex DAGs
- Implement `StepEvaluator` for domain-specific quality metrics
- Use `ModelPromoter` to compare challenger vs incumbent models
