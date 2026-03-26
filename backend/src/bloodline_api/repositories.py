"""Repository helpers for lineage persistence and graph assembly."""

from __future__ import annotations

from collections.abc import Iterable

FactEdge = tuple[str, str, str]


def iter_fact_edges(edges: Iterable[FactEdge]) -> list[FactEdge]:
    """Materialize fact edges as a list for downstream graph builders."""

    return list(edges)
