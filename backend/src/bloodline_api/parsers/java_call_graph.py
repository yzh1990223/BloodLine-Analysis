"""Build a minimal Java method call graph from parsed method scopes."""

from __future__ import annotations

import re

from bloodline_api.parsers.java_symbol_parser import JavaMethodScope


RECEIVER_CALL_PATTERN = re.compile(r"(\w+)\.(\w+)\s*\(")
LOCAL_CALL_PATTERN = re.compile(r"\b(\w+)\s*\(")
EXCLUDED_LOCAL_CALLS = {
    "if",
    "for",
    "while",
    "switch",
    "catch",
    "return",
    "new",
    "super",
    "this",
}


def extract_method_calls(method_body: str) -> list[str]:
    """Extract stable local and receiver-qualified Java method calls."""

    calls: list[str] = []
    seen: set[str] = set()

    for receiver, callee in RECEIVER_CALL_PATTERN.findall(method_body):
        call = f"{receiver}.{callee}"
        if call in seen:
            continue
        seen.add(call)
        calls.append(call)

    receiver_call_spans = [match.span(2) for match in RECEIVER_CALL_PATTERN.finditer(method_body)]
    for match in LOCAL_CALL_PATTERN.finditer(method_body):
        callee = match.group(1)
        if callee in EXCLUDED_LOCAL_CALLS:
            continue
        if any(start <= match.start(1) < end for start, end in receiver_call_spans):
            continue
        if callee in seen:
            continue
        seen.add(callee)
        calls.append(callee)

    return calls


def build_method_call_map(method_scopes: list[JavaMethodScope]) -> dict[str, list[str]]:
    """Build a minimal call map keyed by method name."""

    return {
        scope.method_name: extract_method_calls(scope.body)
        for scope in method_scopes
    }
