"""Example step functions for the seed pipeline.

These demonstrate how to write step functions for detrix pipelines.
Each function receives keyword arguments (from YAML inputs) and
returns a dict of outputs.
"""

from __future__ import annotations

from typing import Any, Dict, List


def load_data(**kwargs: Any) -> Dict[str, Any]:
    """Simulate loading records from a data source."""
    records = [
        {"id": 1, "value": 10.5, "label": "A"},
        {"id": 2, "value": 20.3, "label": "B"},
        {"id": 3, "value": 15.7, "label": "A"},
        {"id": 4, "value": 8.2, "label": "C"},
        {"id": 5, "value": 30.1, "label": "B"},
    ]
    return {"records": records, "count": len(records)}


def process_records(records: List[Dict[str, Any]], **kwargs: Any) -> Dict[str, Any]:
    """Process records: normalize values and compute stats."""
    values = [r["value"] for r in records]
    mean = sum(values) / len(values)
    processed = []
    for r in records:
        processed.append({
            **r,
            "normalized": round(r["value"] / mean, 3),
        })
    stats = {
        "mean": round(mean, 2),
        "min": min(values),
        "max": max(values),
        "count": len(records),
    }
    return {"processed": processed, "stats": stats}


def summarize(
    processed: List[Dict[str, Any]], stats: Dict[str, Any], **kwargs: Any
) -> Dict[str, Any]:
    """Generate a summary from processed records."""
    label_counts: Dict[str, int] = {}
    for r in processed:
        label = r["label"]
        label_counts[label] = label_counts.get(label, 0) + 1

    return {
        "summary": {
            "total_records": stats["count"],
            "value_range": f"{stats['min']} - {stats['max']}",
            "mean_value": stats["mean"],
            "label_distribution": label_counts,
        }
    }
