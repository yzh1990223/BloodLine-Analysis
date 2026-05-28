"""Utility functions for extracting table and column names from SQL text."""

from __future__ import annotations

import logging
import re

from sqlglot import exp, parse_one
from sqlglot.errors import ParseError
from sqlglot.errors import TokenError
from sqlglot.lineage import lineage


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
        if isinstance(target, exp.Schema) and isinstance(target.this, exp.Table):
            return target.this
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


def _walk_lineage_leaves(node, results: list[tuple[str, str]]) -> None:
    """Walk a sqlglot lineage tree and collect leaf source columns."""

    if not node.downstream:
        source_table = node.source
        if isinstance(source_table, exp.Table):
            source_table = _table_name(source_table)
        elif not isinstance(source_table, str):
            # Skip CTEs, subqueries, and other non-table sources
            return
        source_col = node.name
        if source_table and source_col:
            results.append((source_table, source_col))
        return
    for child in node.downstream:
        _walk_lineage_leaves(child, results)


def _extract_output_columns(expression: exp.Expression) -> list[str]:
    """Extract output column names for SELECT-based expressions."""

    output_columns: list[str] = []
    select_expr = None

    if isinstance(expression, exp.Insert):
        select_expr = expression.expression
        # Prefer explicit INSERT column list
        schema = expression.this
        if isinstance(schema, exp.Schema) and schema.expressions:
            return [col.name for col in schema.expressions]
    elif isinstance(expression, exp.Create):
        select_expr = expression.expression
        target = expression.this
        if isinstance(target, exp.Schema) and target.expressions:
            return [col.name for col in target.expressions]
    elif isinstance(expression, exp.Select):
        select_expr = expression

    if isinstance(select_expr, exp.Select):
        for proj in select_expr.expressions:
            if isinstance(proj, exp.Star):
                # Cannot resolve * without schema context
                return []
            alias = proj.alias_or_name
            if alias:
                output_columns.append(alias)

    return output_columns


def _extract_select_column_sources(
    sql: str,
    select_expr: exp.Select,
    target_table: str,
    output_columns: list[str],
) -> list[tuple[str, str, str, str]]:
    """Use sqlglot lineage to map each SELECT projection to its source columns."""

    field_mappings: list[tuple[str, str, str, str]] = []
    for out_col in output_columns:
        try:
            root = lineage(out_col, sql, dialect="mysql")
        except Exception as exc:
            LOGGER.debug("Column lineage failed for '%s': %s", out_col, exc)
            continue

        sources: list[tuple[str, str]] = []
        _walk_lineage_leaves(root, sources)
        for src_table, src_col in sources:
            if src_table and src_col and target_table:
                field_mappings.append((src_table, src_col, target_table, out_col))
    return field_mappings


def _extract_insert_column_lineage(
    expression: exp.Insert,
) -> list[tuple[str, str, str, str]]:
    """Extract column lineage for INSERT ... SELECT using positional mapping."""

    target = _target_table(expression)
    target_table = _table_name(target) if target is not None else None
    if target_table is None:
        return []

    schema = expression.this
    insert_cols: list[str] = []
    if isinstance(schema, exp.Schema) and schema.expressions:
        insert_cols = [col.name for col in schema.expressions]

    select_expr = expression.expression
    if not isinstance(select_expr, exp.Select):
        return []

    select_cols: list[str] = []
    for proj in select_expr.expressions:
        if isinstance(proj, exp.Star):
            return []
        alias = proj.alias_or_name
        if alias:
            select_cols.append(alias)

    if insert_cols and len(insert_cols) != len(select_cols):
        return []

    # When no column list is provided, assume select alias matches target column name
    target_cols = insert_cols if insert_cols else select_cols

    field_mappings: list[tuple[str, str, str, str]] = []
    for target_col, proj in zip(target_cols, select_expr.expressions):
        # Find source columns for this projection expression
        try:
            # Build a mini lineage query using the projection alias
            root = lineage(proj.alias_or_name or proj.sql(), select_expr, dialect="mysql")
        except Exception as exc:
            LOGGER.debug("Insert column lineage failed for '%s': %s", target_col, exc)
            continue

        sources: list[tuple[str, str]] = []
        _walk_lineage_leaves(root, sources)
        for src_table, src_col in sources:
            if src_table and src_col:
                field_mappings.append((src_table, src_col, target_table, target_col))

    return field_mappings


def extract_column_lineage_with_error(
    sql: str,
) -> tuple[list[tuple[str, str, str, str]], str | None]:
    """Extract column-level lineage as (src_table, src_col, dst_table, dst_col) tuples.

    Supports INSERT ... SELECT, CREATE VIEW, and plain SELECT.
    Returns an empty list for statement types that do not have a clear target.
    """

    sql = _normalize_sql_fragment(sql)
    try:
        expression = parse_one(sql, read="mysql")
    except (ParseError, TokenError) as exc:
        LOGGER.warning("Skipping unsupported SQL fragment during column extraction: %s", exc)
        return [], str(exc)
    except RecursionError:
        return [], "SQL 解析递归过深，已跳过该片段。"

    field_mappings: list[tuple[str, str, str, str]] = []

    if isinstance(expression, exp.Insert):
        field_mappings = _extract_insert_column_lineage(expression)
        return field_mappings, None

    target = _target_table(expression)
    target_table = _table_name(target) if target is not None else None

    if isinstance(expression, exp.Create):
        target = expression.this
        if isinstance(target, exp.Schema):
            target_table = _table_name(target.this)
        elif isinstance(target, exp.Table):
            target_table = _table_name(target)

    if target_table is None and not isinstance(expression, exp.Select):
        return [], None

    output_columns = _extract_output_columns(expression)
    if not output_columns:
        return [], None

    select_expr = expression.expression if hasattr(expression, "expression") else expression
    if isinstance(select_expr, exp.Select):
        field_mappings = _extract_select_column_sources(sql, select_expr, target_table or "", output_columns)
    elif isinstance(expression, exp.Select):
        field_mappings = _extract_select_column_sources(sql, expression, target_table or "", output_columns)

    return field_mappings, None
