"""Utility functions for extracting table names from SQL text."""

from __future__ import annotations

import logging
import re

from sqlglot import exp, parse_one
from sqlglot.errors import ParseError
from sqlglot.errors import TokenError


LOGGER = logging.getLogger(__name__)
LINE_CONTINUATION_PATTERN = re.compile(r"\\\s*\n")
HORIZONTAL_WHITESPACE_PATTERN = re.compile(r"[^\S\n]+")
MULTI_NEWLINE_PATTERN = re.compile(r"\n{3,}")
BLOCK_COMMENT_PATTERN = re.compile(r"/\*.*?\*/", re.DOTALL)
WHERE_CONJUNCTION_PATTERN = re.compile(r"\bWHERE\s+(AND|OR)\b", re.IGNORECASE)
LIKE_ORACLE_PLACEHOLDER_PATTERN = re.compile(
    r"(?i)\bLIKE\s+'%'\s*\|\|\s*(?:0|placeholder)\s*\|\|\s*'%'"
)
LIKE_CONCAT_PLACEHOLDER_PATTERN = re.compile(
    r"(?i)\bLIKE\s+CONCAT\s*\(\s*'%'\s*,\s*(?:0|placeholder)\s*,\s*'%'\s*\)"
)
IN_BARE_PLACEHOLDER_PATTERN = re.compile(r"(?i)\bIN\s+(0|placeholder)\s*\)")


def _strip_sql_line_comments(sql: str) -> str:
    """Remove `--` comments while preserving text inside quoted strings."""

    result: list[str] = []
    index = 0
    in_single_quote = False
    in_double_quote = False

    while index < len(sql):
        current = sql[index]
        nxt = sql[index + 1] if index + 1 < len(sql) else ""

        if current == "'" and not in_double_quote:
            if in_single_quote and nxt == "'":
                result.append(current)
                result.append(nxt)
                index += 2
                continue
            in_single_quote = not in_single_quote
            result.append(current)
            index += 1
            continue

        if current == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            result.append(current)
            index += 1
            continue

        if not in_single_quote and not in_double_quote and current == "-" and nxt == "-":
            while index < len(sql) and sql[index] != "\n":
                index += 1
            continue

        result.append(current)
        index += 1

    return "".join(result)


def _normalize_sql_fragment(sql: str) -> str:
    """Normalize obvious transport/concatenation artifacts before parsing."""

    normalized = LINE_CONTINUATION_PATTERN.sub(" ", sql)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = BLOCK_COMMENT_PATTERN.sub(" ", normalized)
    normalized = _strip_sql_line_comments(normalized)
    normalized = LIKE_ORACLE_PLACEHOLDER_PATTERN.sub("LIKE 'placeholder'", normalized)
    normalized = LIKE_CONCAT_PLACEHOLDER_PATTERN.sub("LIKE 'placeholder'", normalized)
    normalized = IN_BARE_PLACEHOLDER_PATTERN.sub(r"IN ( \1 )", normalized)
    normalized = WHERE_CONJUNCTION_PATTERN.sub("WHERE", normalized)
    normalized = HORIZONTAL_WHITESPACE_PATTERN.sub(" ", normalized)
    normalized = "\n".join(line.strip() for line in normalized.split("\n"))
    normalized = MULTI_NEWLINE_PATTERN.sub("\n\n", normalized)
    normalized = normalized.strip()
    return normalized


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

    sql = _normalize_sql_fragment(sql)
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
