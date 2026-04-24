"""Provenance DAG — tracks input → transformation → output lineage.

Stub for Phase 2. Full implementation will build an in-memory DAG
linking raw inputs through step transformations to final outputs,
exportable as an OpenLineage-compatible manifest.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProvenanceNode(BaseModel):
    """A node in the provenance DAG."""

    node_id: str
    node_type: str  # "input", "step", "output"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProvenanceEdge(BaseModel):
    """A directed edge in the provenance DAG."""

    source: str
    target: str
    relation: str = "produced_by"


class ProvenanceGraph(BaseModel):
    """DAG linking inputs → transformations → outputs."""

    nodes: list[ProvenanceNode] = Field(default_factory=list)
    edges: list[ProvenanceEdge] = Field(default_factory=list)
