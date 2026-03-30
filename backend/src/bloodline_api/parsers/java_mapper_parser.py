"""Helpers for extracting minimal MyBatis-style annotation SQL facts."""

from __future__ import annotations

import re
from dataclasses import dataclass


ANNOTATED_METHOD_PATTERN = re.compile(
    r"@(Select|Insert|Update|Delete)\(\"((?:\\.|[^\"\\])*)\"\)\s+[\w<>\[\]\.]+\s+(\w+)\s*\(",
    re.MULTILINE,
)


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
