"""Parse minimal Java method scopes for method-level lineage facts."""

from __future__ import annotations

import re
from dataclasses import dataclass


METHOD_DEF_PATTERN = re.compile(
    r"(?:public|private|protected)?\s*"
    r"(?:static\s+)?"
    r"(?:final\s+)?"
    r"[^;{}=]+?\s+"
    r"(\w+)\s*\((?:[^()]|\([^()]*\))*\)\s*\{",
    re.MULTILINE,
)
DECLARATION_METHOD_PATTERN = re.compile(
    r"(?:public|private|protected)?\s*"
    r"[^;{}=]+?\s+"
    r"(\w+)\s*\((?:[^()]|\([^()]*\))*\)\s*;",
    re.MULTILINE,
)
FIELD_DECL_PATTERN = re.compile(
    r"((?:@\w+(?:\([^)]*\))?\s*)*)(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?([\w<>\[\]\.]+)\s+(\w+)\s*(?:=[^;]*)?;",
    re.MULTILINE,
)
TABLE_NAME_PATTERN = re.compile(r'@TableName\("([^"]+)"\)')
BASE_MAPPER_PATTERN = re.compile(r"extends\s+BaseMapper<\s*([^>]+?)\s*>")
BLOCK_COMMENT_PATTERN = re.compile(r"/\*.*?\*/", re.DOTALL)
LINE_COMMENT_PATTERN = re.compile(r"(?m)//.*$")

@dataclass(slots=True)
class JavaMethodScope:
    """One parsed Java method body with stable minimal facts."""

    method_name: str
    body: str
    start_offset: int
    end_offset: int


@dataclass(slots=True)
class JavaTypeDeclaration:
    """Minimal top-level Java type declaration metadata."""

    kind: str
    type_name: str
    extended_type: str | None
    implemented_types: list[str]


TYPE_DECL_PATTERN = re.compile(
    r"(?:public|private|protected)?\s*"
    r"(?:abstract\s+)?"
    r"(?:final\s+)?"
    r"(class|interface)\s+"
    r"(\w+)"
    r"(?:\s+extends\s+([^{]+?))?"
    r"(?:\s+implements\s+([^{]+?))?"
    r"\s*\{",
    re.MULTILINE,
)


def parse_method_scopes(source: str) -> list[JavaMethodScope]:
    """Extract Java method bodies with naive brace matching."""

    scopes: list[JavaMethodScope] = []
    declaration = parse_type_declaration(source)
    type_name = None if declaration is None else declaration.type_name
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
                method_name=match.group(1),
                body=source[match.end() : cursor - 1],
                start_offset=match.start(),
                end_offset=cursor,
            )
        )
    if type_name:
        constructor_pattern = re.compile(
            r"(?:public|private|protected)?\s*"
            + re.escape(type_name)
            + r"\s*\((?:[^()]|\([^()]*\))*\)\s*\{",
            re.MULTILINE,
        )
        for match in constructor_pattern.finditer(source):
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
                    method_name=type_name,
                    body=source[match.end() : cursor - 1],
                    start_offset=match.start(),
                    end_offset=cursor,
                )
            )
    for match in DECLARATION_METHOD_PATTERN.finditer(source):
        method_name = match.group(1)
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


def _normalize_declared_type_name(type_ref: str) -> str:
    """Normalize one declared Java type reference to its simple outer type name."""

    normalized = re.sub(r"<.*>$", "", type_ref.strip())
    normalized = re.sub(r"\[\]$", "", normalized)
    return normalized.split(".")[-1]


def _strip_java_comments(source: str) -> str:
    """Remove Java line and block comments from a source snippet."""

    without_block_comments = BLOCK_COMMENT_PATTERN.sub(" ", source)
    return LINE_COMMENT_PATTERN.sub("", without_block_comments)


def _primary_type_declaration_match(source: str) -> re.Match[str] | None:
    """Return the first top-level type declaration match if present."""

    return TYPE_DECL_PATTERN.search(_strip_java_comments(source))


def parse_table_name(source: str) -> str | None:
    """Extract a direct @TableName value from a Java entity declaration."""

    cleaned_source = _strip_java_comments(source)
    match = _primary_type_declaration_match(cleaned_source)
    if match is None:
        return None

    matches = TABLE_NAME_PATTERN.findall(cleaned_source[: match.start()])
    if not matches:
        return None
    return matches[-1].strip()


def parse_basemapper_entity(source: str) -> str | None:
    """Extract the entity type bound to a BaseMapper declaration."""

    cleaned_source = _strip_java_comments(source)
    match = _primary_type_declaration_match(cleaned_source)
    if match is None:
        return None

    cleaned_header = cleaned_source[match.start() : match.end()]
    base_match = BASE_MAPPER_PATTERN.search(cleaned_header)
    if base_match is None:
        return None
    return _normalize_declared_type_name(base_match.group(1))


def parse_type_declaration(source: str) -> JavaTypeDeclaration | None:
    """Extract one top-level class/interface declaration with implemented types."""

    match = TYPE_DECL_PATTERN.search(source)
    if match is None:
        return None

    kind = match.group(1)
    type_name = match.group(2)
    extended_type = None
    if match.group(3):
        extended_type = match.group(3).strip()
    implemented_types: list[str] = []
    raw_type_list = match.group(4) if kind == "class" else match.group(3)
    if kind == "interface":
        raw_type_list = match.group(3)
    if raw_type_list:
        for item in raw_type_list.split(","):
            normalized = _normalize_declared_type_name(item)
            if normalized and normalized not in implemented_types:
                implemented_types.append(normalized)

    return JavaTypeDeclaration(
        kind=kind,
        type_name=type_name,
        extended_type=extended_type,
        implemented_types=implemented_types,
    )


def parse_field_types(source: str, method_scopes: list[JavaMethodScope] | None = None) -> dict[str, str]:
    """Extract top-level field declaration types keyed by receiver variable name."""

    scopes = method_scopes if method_scopes is not None else parse_method_scopes(source)
    field_types: dict[str, str] = {}

    for match in FIELD_DECL_PATTERN.finditer(source):
        start = match.start()
        if any(scope.start_offset <= start < scope.end_offset for scope in scopes):
            continue
        field_types[match.group(3)] = match.group(2)

    return field_types


def parse_implemented_types(source: str) -> list[str]:
    """Extract implemented interface names from the primary class declaration."""

    declaration = parse_type_declaration(source)
    if declaration is None or declaration.kind != "class":
        return []
    return declaration.implemented_types


def parse_extended_type(source: str) -> str | None:
    """Extract the primary extended type reference from the top-level declaration."""

    declaration = parse_type_declaration(source)
    if declaration is None:
        return None
    return declaration.extended_type
