"""Parse minimal Java method scopes for method-level lineage facts."""

from __future__ import annotations

import re
from dataclasses import dataclass


METHOD_DEF_PATTERN = re.compile(
    r"(public|private|protected)\s+[\w<>\[\]]+\s+(\w+)\s*\([^)]*\)\s*\{"
)
DECLARATION_METHOD_PATTERN = re.compile(
    r"(public|private|protected)?\s*[\w<>\[\]\.]+\s+(\w+)\s*\([^)]*\)\s*;",
    re.MULTILINE,
)

@dataclass(slots=True)
class JavaMethodScope:
    """One parsed Java method body with stable minimal facts."""

    method_name: str
    body: str
    start_offset: int
    end_offset: int


def parse_method_scopes(source: str) -> list[JavaMethodScope]:
    """Extract Java method bodies with naive brace matching."""

    scopes: list[JavaMethodScope] = []
    for match in METHOD_DEF_PATTERN.finditer(source):
        depth = 1
        cursor = match.end()
        while cursor < len(source) and depth > 0:
            if source[cursor] == "{":
                depth += 1
            elif source[cursor] == "}":
                depth -= 1
            cursor += 1
        scopes.append(
            JavaMethodScope(
                method_name=match.group(2),
                body=source[match.end() : cursor - 1],
                start_offset=match.start(),
                end_offset=cursor,
            )
        )
    for match in DECLARATION_METHOD_PATTERN.finditer(source):
        method_name = match.group(2)
        if any(scope.method_name == method_name for scope in scopes):
            continue
        scopes.append(
            JavaMethodScope(
                method_name=method_name,
                body="",
                start_offset=match.start(),
                end_offset=match.end(),
            )
        )
    return scopes
