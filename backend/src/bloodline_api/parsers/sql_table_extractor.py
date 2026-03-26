from __future__ import annotations

from sqlglot import exp, parse_one
from sqlglot.errors import ParseError


def _table_sql(table: exp.Table) -> str:
    return table.sql(dialect="mysql")


def _target_table(expression: exp.Expression) -> exp.Table | None:
    if isinstance(expression, (exp.Insert, exp.Update, exp.Delete, exp.Create)):
        target = expression.this
        if isinstance(target, exp.Table):
            return target
    return None


def extract_tables(sql: str) -> tuple[set[str], set[str]]:
    try:
        expression = parse_one(sql, read="mysql")
    except ParseError:
        return set(), set()

    target = _target_table(expression)
    target_sql = _table_sql(target) if target is not None else None

    tables = {_table_sql(table) for table in expression.find_all(exp.Table)}
    reads = set(tables)
    writes: set[str] = set()

    if target_sql is not None:
        writes.add(target_sql)
        reads.discard(target_sql)

    return reads, writes
