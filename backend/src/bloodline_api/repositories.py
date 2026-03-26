"""Repository helpers for lineage persistence and graph assembly."""

from __future__ import annotations

from collections.abc import Iterable

from bloodline_api.models import Edge

FactEdge = tuple[str, str, str]


def iter_fact_edges(edges: Iterable[FactEdge]) -> list[FactEdge]:
    """Materialize fact edges as a list for downstream graph builders."""

    return list(edges)


def materialize_derived_flow_edges(flow_node_pairs: Iterable[tuple[int, int]]) -> list[Edge]:
    """Create in-memory derived FLOWS_TO edges before they are persisted."""

    return [
        Edge(
            type="FLOWS_TO",
            src_node_id=src_node_id,
            dst_node_id=dst_node_id,
            is_derived=True,
            payload={},
        )
        for src_node_id, dst_node_id in flow_node_pairs
    ]
