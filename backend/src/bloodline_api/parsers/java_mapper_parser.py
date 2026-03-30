"""Helpers for extracting minimal MyBatis-style annotation and XML SQL facts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from bloodline_api.connectors.java_source_reader import read_java_source


ANNOTATED_METHOD_PATTERN = re.compile(
    r"@(Select|Insert|Update|Delete)\(\"((?:\\.|[^\"\\])*)\"\)\s+[\w<>\[\]\.]+\s+(\w+)\s*\(",
    re.MULTILINE,
)
XML_METHOD_PATTERN = re.compile(
    r"<(select|insert|update|delete)\s+[^>]*id=\"([^\"]+)\"[^>]*>(.*?)</\1>",
    re.IGNORECASE | re.DOTALL,
)
XML_TAG_PATTERN = re.compile(r"<[^>]+>")


@dataclass(slots=True)
class AnnotatedMethodSql:
    """One SQL-bearing annotation bound to one Java method name."""

    method_name: str
    sql: str
    start_offset: int


def extract_annotated_method_sql(source: str) -> list[AnnotatedMethodSql]:
    """Extract stable MyBatis-style annotation SQL bound to method names."""

    return [
        AnnotatedMethodSql(
            method_name=match.group(3),
            sql=match.group(2).strip(),
            start_offset=match.start(),
        )
        for match in ANNOTATED_METHOD_PATTERN.finditer(source)
    ]


def _normalize_xml_sql(sql_fragment: str) -> str:
    """Collapse static XML SQL text into a parser-friendly string."""

    without_tags = XML_TAG_PATTERN.sub(" ", sql_fragment)
    return " ".join(without_tags.split()).strip()


def extract_xml_method_sql(java_path: Path) -> list[AnnotatedMethodSql]:
    """Extract static SQL from a sibling MyBatis XML mapper when present."""

    xml_path = java_path.with_suffix(".xml")
    if not xml_path.exists():
        return []

    source = read_java_source(xml_path)
    statements: list[AnnotatedMethodSql] = []
    for match in XML_METHOD_PATTERN.finditer(source):
        sql = _normalize_xml_sql(match.group(3))
        if not sql:
            continue
        statements.append(
            AnnotatedMethodSql(
                method_name=match.group(2),
                sql=sql,
                start_offset=match.start(),
            )
        )
    return statements
