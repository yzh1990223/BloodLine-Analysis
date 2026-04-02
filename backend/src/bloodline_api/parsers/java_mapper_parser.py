"""Helpers for extracting minimal MyBatis-style annotation and XML SQL facts."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path

from bloodline_api.connectors.java_source_reader import read_java_source


ANNOTATED_METHOD_PATTERN = re.compile(
    r"@(Select|Insert|Update|Delete)\s*"
    r"\(\s*(?:value\s*=\s*)?"
    r"(.+?)"
    r"\)\s+[\w<>\[\]\.]+\s+(\w+)\s*\(",
    re.MULTILINE | re.DOTALL,
)
ANNOTATED_SQL_STRING_PATTERN = re.compile(r"\"((?:\\.|[^\"\\])*)\"")
XML_METHOD_PATTERN = re.compile(
    r"<(select|insert|update|delete)\s+[^>]*id=\"([^\"]+)\"[^>]*>(.*?)</\1>",
    re.IGNORECASE | re.DOTALL,
)
XML_TAG_PATTERN = re.compile(r"<[^>]+>")
XML_WHERE_OPEN_PATTERN = re.compile(r"<where[^>]*>", re.IGNORECASE)
XML_WHERE_CLOSE_PATTERN = re.compile(r"</where>", re.IGNORECASE)
XML_SET_OPEN_PATTERN = re.compile(r"<set[^>]*>", re.IGNORECASE)
XML_SET_CLOSE_PATTERN = re.compile(r"</set>", re.IGNORECASE)
XML_FOREACH_OPEN_PATTERN = re.compile(r"<foreach[^>]*open=\"([^\"]*)\"[^>]*close=\"([^\"]*)\"[^>]*>", re.IGNORECASE)
XML_FOREACH_CLOSE_PATTERN = re.compile(r"</foreach>", re.IGNORECASE)
MYBATIS_PARAM_PATTERN = re.compile(r"#\{[^}]+\}")
MYBATIS_TEXT_PARAM_PATTERN = re.compile(r"\$\{[^}]+\}")


@dataclass(slots=True)
class AnnotatedMethodSql:
    """One SQL-bearing annotation bound to one Java method name."""

    method_name: str
    sql: str
    start_offset: int
    end_offset: int


def _decode_java_string_literal(fragment: str) -> str:
    """Decode common Java string escapes into parser-friendly text."""

    decoded = bytes(fragment, "utf-8").decode("unicode_escape")
    decoded = (
        decoded.replace("\\n", "\n")
        .replace("\\t", "\t")
        .replace("\\r", "\r")
        .replace('\\"', '"')
        .replace("\\\\", "\\")
    )
    return decoded


def decode_java_string_literal(fragment: str) -> str:
    """Shared public wrapper for decoding Java string literal content."""

    return _decode_java_string_literal(fragment)


def extract_annotated_method_sql(source: str) -> list[AnnotatedMethodSql]:
    """Extract stable MyBatis-style annotation SQL bound to method names."""

    return [
        AnnotatedMethodSql(
            method_name=match.group(3),
            sql=_normalize_mapper_sql(
                " ".join(
                    _decode_java_string_literal(part).strip()
                    for part in ANNOTATED_SQL_STRING_PATTERN.findall(match.group(2))
                    if part.strip()
                )
            ),
            start_offset=match.start(),
            end_offset=match.end(),
        )
        for match in ANNOTATED_METHOD_PATTERN.finditer(source)
        if ANNOTATED_SQL_STRING_PATTERN.findall(match.group(2))
    ]


def _normalize_mapper_sql(sql_fragment: str) -> str:
    """Normalize mapper SQL text that already has tags stripped."""

    normalized = MYBATIS_PARAM_PATTERN.sub("0", sql_fragment)
    normalized = MYBATIS_TEXT_PARAM_PATTERN.sub("placeholder", normalized)
    normalized = " ".join(normalized.split()).strip()
    return normalized


def _normalize_xml_sql(sql_fragment: str) -> str:
    """Collapse static XML SQL text into a parser-friendly string."""

    normalized = html.unescape(sql_fragment)
    normalized = XML_WHERE_OPEN_PATTERN.sub(" WHERE ", normalized)
    normalized = XML_WHERE_CLOSE_PATTERN.sub(" ", normalized)
    normalized = XML_SET_OPEN_PATTERN.sub(" SET ", normalized)
    normalized = XML_SET_CLOSE_PATTERN.sub(" ", normalized)
    normalized = XML_FOREACH_OPEN_PATTERN.sub(lambda match: f" {match.group(1) or '('} ", normalized)
    normalized = XML_FOREACH_CLOSE_PATTERN.sub(" ) ", normalized)
    normalized = XML_TAG_PATTERN.sub(" ", normalized)
    normalized = MYBATIS_PARAM_PATTERN.sub("0", normalized)
    normalized = MYBATIS_TEXT_PARAM_PATTERN.sub("placeholder", normalized)
    normalized = normalized.replace("]]>", " ")
    normalized = " ".join(normalized.split()).strip()
    return normalized


def extract_xml_method_sql(java_path: Path) -> list[AnnotatedMethodSql]:
    """Extract static SQL from a sibling MyBatis XML mapper when present."""

    candidate_paths = [java_path.with_suffix(".xml")]
    mapper_resources_path = java_path.parent / "resources" / "mapper" / f"{java_path.stem}.xml"
    candidate_paths.append(mapper_resources_path)

    xml_path = next((path for path in candidate_paths if path.exists()), None)
    if xml_path is None:
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
                end_offset=match.end(),
            )
        )
    return statements
