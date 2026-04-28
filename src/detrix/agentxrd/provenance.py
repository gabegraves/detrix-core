from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from detrix.runtime.provenance import ProvenanceEdge, ProvenanceGraph, ProvenanceNode


def build_agentxrd_provenance_dag(
    *,
    detrix_artifact: Path,
    trace_packet_map: Path,
    row_packets: Path,
    output_path: Path,
) -> ProvenanceGraph:
    artifact = _load_json(detrix_artifact)
    maps = _load_jsonl(trace_packet_map)
    packets = {str(row["sample_id"]): row for row in _load_jsonl(row_packets)}
    terminals = artifact["terminal_routes"]
    scores = {str(row["sample_id"]): row for row in artifact["langfuse_score_evidence"]}
    recon = {
        str(row["sample_id"]): row
        for row in artifact["deterministic_gate_reconciliation"]["rows"]
    }

    nodes: dict[str, ProvenanceNode] = {}
    edges: list[ProvenanceEdge] = []

    for mapping in maps:
        sample_id = str(mapping["sample_id"])
        trace_id = str(mapping.get("trace_id") or f"trace:{sample_id}")
        packet = packets.get(sample_id, {})
        packet_id = f"packet:{sample_id}"
        route_id = f"terminal:{sample_id}"
        training_id = f"training:{sample_id}"

        nodes[f"sample:{sample_id}"] = ProvenanceNode(
            node_id=f"sample:{sample_id}",
            node_type="sample",
            metadata={"sample_id": sample_id},
        )
        nodes[trace_id] = ProvenanceNode(
            node_id=trace_id,
            node_type="trace",
            metadata={"observation_id": mapping.get("observation_id")},
        )
        nodes[packet_id] = ProvenanceNode(
            node_id=packet_id,
            node_type="pxrd_packet",
            metadata=packet,
        )
        refinement_id = f"refinement:{sample_id}"
        nodes[refinement_id] = ProvenanceNode(
            node_id=refinement_id,
            node_type="refinement_evidence",
            metadata=packet.get("pawley_rietveld_metrics", {}),
        )
        nodes[route_id] = ProvenanceNode(
            node_id=route_id,
            node_type="terminal_route",
            metadata=terminals.get(sample_id, {}),
        )
        nodes[training_id] = ProvenanceNode(
            node_id=training_id,
            node_type="training_route",
            metadata={
                "judge_score": scores.get(sample_id, {}),
                "reconciliation": recon.get(sample_id, {}),
            },
        )
        edges.extend(
            [
                ProvenanceEdge(
                    source=f"sample:{sample_id}", target=trace_id, relation="observed_as"
                ),
                ProvenanceEdge(
                    source=trace_id, target=packet_id, relation="maps_to_packet"
                ),
                ProvenanceEdge(
                    source=packet_id,
                    target=refinement_id,
                    relation="has_refinement_evidence",
                ),
                ProvenanceEdge(
                    source=packet_id,
                    target=route_id,
                    relation="produces_terminal_route",
                ),
                ProvenanceEdge(
                    source=route_id,
                    target=training_id,
                    relation="governs_training_route",
                ),
            ]
        )
        for index, candidate in enumerate(packet.get("candidate_cif_provenance", [])):
            candidate_id = f"candidate:{sample_id}:{index}"
            source_id = f"source_cif:{sample_id}:{index}"
            nodes[candidate_id] = ProvenanceNode(
                node_id=candidate_id,
                node_type="candidate_cif",
                metadata=candidate,
            )
            nodes[source_id] = ProvenanceNode(
                node_id=source_id,
                node_type="source_cif",
                metadata={
                    "cif_path": candidate.get("cif_path"),
                    "source": candidate.get("source"),
                    "support_only": candidate.get("support_only"),
                    "accept_eligible": candidate.get("accept_eligible"),
                    "generated_structure": candidate.get("generated_structure"),
                    "generated_provenance": candidate.get("generated_provenance"),
                },
            )
            edges.extend(
                [
                    ProvenanceEdge(
                        source=packet_id, target=candidate_id, relation="has_candidate"
                    ),
                    ProvenanceEdge(
                        source=candidate_id,
                        target=source_id,
                        relation="derived_from_source",
                    ),
                    ProvenanceEdge(
                        source=source_id,
                        target=route_id,
                        relation="constrains_terminal_route",
                    ),
                ]
            )

    graph = ProvenanceGraph(nodes=list(nodes.values()), edges=edges)
    _write_graph(output_path, graph)
    return graph


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return payload


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_graph(path: Path, graph: ProvenanceGraph) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for node in graph.nodes:
            file.write(
                json.dumps({"record_type": "node", **node.model_dump()}, sort_keys=True)
                + "\n"
            )
        for edge in graph.edges:
            file.write(
                json.dumps({"record_type": "edge", **edge.model_dump()}, sort_keys=True)
                + "\n"
            )
