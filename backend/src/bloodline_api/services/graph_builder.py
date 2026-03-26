"""Derive table-level flows from fact edges."""

from __future__ import annotations

from collections import defaultdict

FactEdge = tuple[str, str, str]
TableFlow = tuple[str, str]


def build_table_flows(fact_edges: list[FactEdge]) -> list[TableFlow]:
    """Return unique table-to-table flows derived from fact edges.

    The MVP derives flows only within the same actor node (`src`).
    """

    reads_by_actor: dict[str, set[str]] = defaultdict(set)
    writes_by_actor: dict[str, set[str]] = defaultdict(set)

    for edge_type, src, dst in fact_edges:
        if edge_type == "READS":
            reads_by_actor[src].add(dst)
        elif edge_type == "WRITES":
            writes_by_actor[src].add(dst)

    flows: set[TableFlow] = set()
    for actor, read_tables in reads_by_actor.items():
        write_tables = writes_by_actor.get(actor)
        if not write_tables:
            continue
        for read_table in read_tables:
            for write_table in write_tables:
                flows.add((read_table, write_table))

    return sorted(flows)
