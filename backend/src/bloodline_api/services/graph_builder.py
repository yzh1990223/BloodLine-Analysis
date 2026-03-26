"""Derive table-level flows from fact edges."""

from __future__ import annotations

from collections import defaultdict

FactEdge = tuple[str, str, str]
TableFlow = tuple[str, str]


def _actor_scope(actor: str) -> str:
    """Collapse parser-specific actor IDs to the scope used for flow derivation."""

    return actor.split("::", 1)[0]


def build_table_flows(fact_edges: list[FactEdge]) -> list[TableFlow]:
    """Return unique table-to-table flows derived from fact edges.

    The MVP derives flows only within the same actor scope. Parser-shaped
    step actors like ``transformation::step`` collapse to their transformation
    prefix so reads and writes from different steps can still connect.
    """

    reads_by_actor: dict[str, set[str]] = defaultdict(set)
    writes_by_actor: dict[str, set[str]] = defaultdict(set)

    for edge_type, src, dst in fact_edges:
        actor = _actor_scope(src)
        if edge_type == "READS":
            reads_by_actor[actor].add(dst)
        elif edge_type == "WRITES":
            writes_by_actor[actor].add(dst)

    flows: set[TableFlow] = set()
    for actor, read_tables in reads_by_actor.items():
        write_tables = writes_by_actor.get(actor)
        if not write_tables:
            continue
        for read_table in read_tables:
            for write_table in write_tables:
                flows.add((read_table, write_table))

    return sorted(flows)
