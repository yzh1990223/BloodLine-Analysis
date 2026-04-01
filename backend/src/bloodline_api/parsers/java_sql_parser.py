"""Parse Java files into module-level and statement-level table facts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from bloodline_api.connectors.java_source_reader import read_java_source
from bloodline_api.parsers.java_call_graph import build_method_call_map
from bloodline_api.parsers.java_mapper_parser import extract_annotated_method_sql
from bloodline_api.parsers.java_mapper_parser import extract_xml_method_sql
from bloodline_api.parsers.java_symbol_parser import parse_field_types
from bloodline_api.parsers.java_symbol_parser import parse_implemented_types
from bloodline_api.parsers.java_symbol_parser import parse_method_scopes
from bloodline_api.parsers.sql_table_extractor import extract_tables

# Only string literals that look like SQL statements are considered in the MVP.
SQL_STRING_PATTERN = re.compile(r'"((?:\\.|[^"\\])*)"')
SQL_START_PATTERN = re.compile(r"^(select|insert|update|delete|create)\b", re.IGNORECASE)
ANNOTATION_PREFIX_PATTERN = re.compile(r"@\w+\($")


@dataclass(slots=True)
class JavaModuleParseResult:
    """Normalized table facts extracted from one Java compilation unit."""

    module_name: str
    read_tables: list[str]
    write_tables: list[str]
    statements: list["JavaSqlStatement"]
    methods: dict[str, "JavaMethodFact"]
    receiver_types: dict[str, str]
    implemented_types: list[str]


@dataclass(slots=True)
class JavaSqlStatement:
    """One SQL-bearing Java string literal preserved as an independent fact scope."""

    statement_id: str
    read_tables: list[str]
    write_tables: list[str]


@dataclass(slots=True)
class JavaMethodFact:
    """Minimal method-scoped facts used by later call-graph work."""

    method_name: str
    statement_ids: list[str]
    calls: list[str]


class JavaSqlParser:
    """Extract table-level lineage facts from simple SQL-bearing Java files."""

    def parse_file(self, path: Path) -> JavaModuleParseResult:
        """Parse one Java file into de-duplicated read/write table lists."""

        source = read_java_source(path)
        reads: set[str] = set()
        writes: set[str] = set()
        statements: list[JavaSqlStatement] = []
        method_scopes = parse_method_scopes(source)
        receiver_types = parse_field_types(source, method_scopes)
        implemented_types = parse_implemented_types(source)
        method_call_map = build_method_call_map(method_scopes)
        methods = {
            scope.method_name: JavaMethodFact(
                method_name=scope.method_name,
                statement_ids=[],
                calls=method_call_map.get(scope.method_name, []),
            )
            for scope in method_scopes
        }

        for index, match in enumerate(SQL_STRING_PATTERN.finditer(source)):
            sql = match.group(1).strip()
            if not SQL_START_PATTERN.match(sql):
                continue
            line_prefix = source[max(0, source.rfind("\n", 0, match.start()) + 1) : match.start()]
            if ANNOTATION_PREFIX_PATTERN.search(line_prefix.strip()):
                continue
            statement_id = f"sql_{index}"
            sql_reads, sql_writes = extract_tables(sql)
            statements.append(
                JavaSqlStatement(
                    statement_id=statement_id,
                    read_tables=sorted(sql_reads),
                    write_tables=sorted(sql_writes),
                )
            )
            for scope in method_scopes:
                if scope.start_offset <= match.start() <= scope.end_offset:
                    methods[scope.method_name].statement_ids.append(statement_id)
                    break
            reads.update(sql_reads)
            writes.update(sql_writes)

        next_statement_index = len(statements)
        for annotated in [*extract_annotated_method_sql(source), *extract_xml_method_sql(path)]:
            statement_id = f"sql_{next_statement_index}"
            next_statement_index += 1
            sql_reads, sql_writes = extract_tables(annotated.sql)
            if not sql_reads and not sql_writes:
                continue
            statements.append(
                JavaSqlStatement(
                    statement_id=statement_id,
                    read_tables=sorted(sql_reads),
                    write_tables=sorted(sql_writes),
                )
            )
            methods.setdefault(
                annotated.method_name,
                JavaMethodFact(method_name=annotated.method_name, statement_ids=[], calls=[]),
            ).statement_ids.append(statement_id)
            reads.update(sql_reads)
            writes.update(sql_writes)

        return JavaModuleParseResult(
            module_name=path.stem,
            read_tables=sorted(reads),
            write_tables=sorted(writes),
            statements=statements,
            methods=methods,
            receiver_types=receiver_types,
            implemented_types=implemented_types,
        )
