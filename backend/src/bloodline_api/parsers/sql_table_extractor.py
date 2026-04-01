"""Utility functions for extracting table names from SQL text."""

from __future__ import annotations

import logging

from sqlglot import exp, parse_one
from sqlglot.errors import ParseError
from sqlglot.errors import TokenError


LOGGER = logging.getLogger(__name__)


def _table_name(table: exp.Table) -> str:
    """Return the physical table identifier without aliases."""

    return ".".join(part.this for part in table.parts)


def _target_table(expression: exp.Expression) -> exp.Table | None:
    """Return the write target when the SQL statement has one."""

    if isinstance(expression, (exp.Insert, exp.Update, exp.Delete, exp.Create)):
        target = expression.this
        if isinstance(target, exp.Table):
            return target
    return None


def _cte_aliases(expression: exp.Expression) -> set[str]:
    """Return normalized CTE aliases so they can be excluded from physical table facts."""

    aliases: set[str] = set()
    for cte in expression.find_all(exp.CTE):
        alias = cte.alias_or_name
        if alias:
            aliases.add(alias.lower())
    return aliases


def extract_tables_with_error(sql: str) -> tuple[set[str], set[str], str | None]:
    """Split SQL table usage into read tables and write tables, preserving parse errors."""

    try:
        expression = parse_one(sql, read="mysql")
    except (ParseError, TokenError) as exc:
        LOGGER.warning("Skipping unsupported SQL fragment during table extraction: %s", exc)
        return set(), set(), str(exc)

    target = _target_table(expression)
    target_sql = _table_name(target) if target is not None else None
    cte_aliases = _cte_aliases(expression)

    tables = {
        table_name
        for table in expression.find_all(exp.Table)
        if (table_name := _table_name(table)) and table_name.lower() not in cte_aliases
    }
    reads = set(tables)
    writes: set[str] = set()

    if target_sql is not None:
        writes.add(target_sql)
        reads.discard(target_sql)

    return reads, writes, None


def extract_tables(sql: str) -> tuple[set[str], set[str]]:
    """Split SQL table usage into read tables and write tables."""

    reads, writes, _error = extract_tables_with_error(sql)
    return reads, writes
