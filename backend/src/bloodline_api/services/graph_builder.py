"""Derive table-level flows from fact edges."""

from __future__ import annotations

FactEdge = tuple[str, str, str]
TableFlow = tuple[str, str]


def build_table_flows(fact_edges: list[FactEdge]) -> list[TableFlow]:
    """Return unique table-to-table flows derived from fact edges.

    The MVP treats table flows as the cross-product of all observed read tables
    and write tables in the fact edge set.
    """

    read_tables: set[str] = set()
    write_tables: set[str] = set()

    for edge_type, _src, dst in fact_edges:
        if edge_type == "READS":
            read_tables.add(dst)
        elif edge_type == "WRITES":
            write_tables.add(dst)

    flows: set[TableFlow] = set()
    for read_table in read_tables:
        for write_table in write_tables:
            flows.add((read_table, write_table))

    return sorted(flows)
