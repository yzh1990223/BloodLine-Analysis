from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from bloodline_api.connectors.java_source_reader import read_java_source
from bloodline_api.parsers.sql_table_extractor import extract_tables

SQL_STRING_PATTERN = re.compile(r'"((?:\\.|[^"\\])*)"')
SQL_START_PATTERN = re.compile(r"^(select|insert|update|delete|create)\b", re.IGNORECASE)


@dataclass(slots=True)
class JavaModuleParseResult:
    module_name: str
    read_tables: list[str]
    write_tables: list[str]


class JavaSqlParser:
    def parse_file(self, path: Path) -> JavaModuleParseResult:
        source = read_java_source(path)
        reads: set[str] = set()
        writes: set[str] = set()

        for match in SQL_STRING_PATTERN.finditer(source):
            sql = match.group(1).strip()
            if not SQL_START_PATTERN.match(sql):
                continue
            sql_reads, sql_writes = extract_tables(sql)
            reads.update(sql_reads)
            writes.update(sql_writes)

        return JavaModuleParseResult(
            module_name=path.stem,
            read_tables=sorted(reads),
            write_tables=sorted(writes),
        )
