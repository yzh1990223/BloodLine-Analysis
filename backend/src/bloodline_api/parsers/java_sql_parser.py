"""Parse Java files into module-level and statement-level table facts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from bloodline_api.connectors.java_source_reader import read_java_source
from bloodline_api.parsers.java_symbol_parser import extract_receiver_calls
from bloodline_api.parsers.java_symbol_parser import parse_method_scopes
from bloodline_api.parsers.sql_table_extractor import extract_tables

# Only string literals that look like SQL statements are considered in the MVP.
SQL_STRING_PATTERN = re.compile(r'"((?:\\.|[^"\\])*)"')
SQL_START_PATTERN = re.compile(r"^(select|insert|update|delete|create)\b", re.IGNORECASE)


@dataclass(slots=True)
class JavaModuleParseResult:
    """Normalized table facts extracted from one Java compilation unit."""

    module_name: str
    read_tables: list[str]
    write_tables: list[str]
    statements: list["JavaSqlStatement"]
    methods: dict[str, "JavaMethodFact"]


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
        methods = {
            scope.method_name: JavaMethodFact(
                method_name=scope.method_name,
                statement_ids=[],
                calls=extract_receiver_calls(scope.body),
            )
            for scope in parse_method_scopes(source)
        }

        for index, match in enumerate(SQL_STRING_PATTERN.finditer(source)):
            sql = match.group(1).strip()
            if not SQL_START_PATTERN.match(sql):
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
            for scope in parse_method_scopes(source):
                if scope.start_offset <= match.start() <= scope.end_offset:
                    methods[scope.method_name].statement_ids.append(statement_id)
                    break
            reads.update(sql_reads)
            writes.update(sql_writes)

        return JavaModuleParseResult(
            module_name=path.stem,
            read_tables=sorted(reads),
            write_tables=sorted(writes),
            statements=statements,
            methods=methods,
        )
