"""Provenance DAG — tracks input → transformation → output lineage.

Stub for Phase 2. Full implementation will build an in-memory DAG
linking raw inputs through step transformations to final outputs,
exportable as an OpenLineage-compatible manifest.
"""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class ProvenanceNode(BaseModel):
    """A node in the provenance DAG."""

    node_id: str
    node_type: str  # "input", "step", "output"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProvenanceEdge(BaseModel):
    """A directed edge in the provenance DAG."""

    source: str
    target: str
    relation: str = "produced_by"


class ProvenanceGraph(BaseModel):
    """DAG linking inputs → transformations → outputs."""

    nodes: List[ProvenanceNode] = Field(default_factory=list)
    edges: List[ProvenanceEdge] = Field(default_factory=list)
