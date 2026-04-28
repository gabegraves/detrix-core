import json
from pathlib import Path

from detrix.agentxrd.provenance import build_agentxrd_provenance_dag

FIXTURE_ROOT = Path("/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics")
BINARY20 = FIXTURE_ROOT / "binary20_governed_judge_cohort_v0"


def test_provenance_dag_links_trace_packet_candidate_and_export_route(tmp_path):
    output = tmp_path / "provenance_dag.jsonl"

    graph = build_agentxrd_provenance_dag(
        detrix_artifact=BINARY20 / "detrix_run_artifact.json",
        trace_packet_map=BINARY20 / "trace_to_pxrd_packet_map.jsonl",
        row_packets=BINARY20 / "row_packets.jsonl",
        output_path=output,
    )

    assert graph.nodes
    assert graph.edges
    node_types = {node.node_type for node in graph.nodes}
    assert {
        "sample",
        "trace",
        "pxrd_packet",
        "candidate_cif",
        "source_cif",
        "refinement_evidence",
        "terminal_route",
        "training_route",
    } <= node_types

    rows = [json.loads(line) for line in output.read_text().splitlines()]
    assert any(row["record_type"] == "node" for row in rows)
    assert any(row["record_type"] == "edge" for row in rows)
