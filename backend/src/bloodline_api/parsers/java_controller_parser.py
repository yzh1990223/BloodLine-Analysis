"""Parse Spring MVC controller routes into stable API endpoint facts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from bloodline_api.connectors.java_source_reader import read_java_source
from bloodline_api.parsers.java_symbol_parser import parse_method_scopes


CLASS_DECL_PATTERN = re.compile(
    r"((?:@\w+(?:\([^)]*\))?\s*)*)\b(?:public\s+)?(?:final\s+)?class\s+(\w+)",
    re.MULTILINE,
)
METHOD_DECL_PATTERN = re.compile(
    r"((?:@\w+(?:\((?:[^()]|\([^()]*\))*\))?\s*)*)"
    r"(public|private|protected)\s+"
    r"[^;{}=]+?\s+"
    r"(\w+)\s*\((?:[^()]|\([^()]*\))*\)\s*\{",
    re.MULTILINE,
)
ANNOTATION_PATTERN = re.compile(r"@(\w+)(?:\((.*?)\))?", re.DOTALL)
STRING_LITERAL_PATTERN = re.compile(r'"([^"]+)"')
REQUEST_METHOD_PATTERN = re.compile(r"RequestMethod\.(GET|POST|PUT|DELETE|PATCH)")

HTTP_METHOD_BY_ANNOTATION = {
    "GetMapping": "GET",
    "PostMapping": "POST",
    "PutMapping": "PUT",
    "DeleteMapping": "DELETE",
    "PatchMapping": "PATCH",
}


@dataclass(slots=True)
class JavaApiEndpointFact:
    """One stable HTTP endpoint bound to a concrete controller method."""

    endpoint_key: str
    route: str
    http_method: str
    controller_module_name: str
    method_name: str


def _extract_route_path(arguments: str | None) -> str:
    if not arguments:
        return ""
    values = STRING_LITERAL_PATTERN.findall(arguments)
    return values[0] if values else ""


def _normalize_path(*parts: str) -> str:
    cleaned = [part.strip() for part in parts if part and part.strip()]
    if not cleaned:
        return "/"
    joined = "/".join(part.strip("/") for part in cleaned if part.strip("/"))
    normalized = "/" + joined if joined else "/"
    return re.sub(r"/+", "/", normalized)


def _extract_request_mapping_method(arguments: str | None) -> str | None:
    if not arguments:
        return None
    match = REQUEST_METHOD_PATTERN.search(arguments)
    if match is None:
        return None
    return match.group(1)


def _extract_base_path(annotation_block: str) -> str:
    for annotation_name, arguments in ANNOTATION_PATTERN.findall(annotation_block):
        if annotation_name == "RequestMapping":
            return _extract_route_path(arguments)
    return ""


def _is_controller(annotation_block: str) -> bool:
    annotation_names = {name for name, _arguments in ANNOTATION_PATTERN.findall(annotation_block)}
    return "RestController" in annotation_names or "Controller" in annotation_names


def parse_controller_endpoints(path: Path) -> list[JavaApiEndpointFact]:
    """Extract stable HTTP endpoint facts from one Spring MVC controller file."""

    source = read_java_source(path)
    class_match = CLASS_DECL_PATTERN.search(source)
    if class_match is None:
        return []
    class_annotations = class_match.group(1)
    if not _is_controller(class_annotations):
        return []

    base_path = _extract_base_path(class_annotations)
    controller_module_name = path.stem
    method_scopes = {scope.method_name: scope for scope in parse_method_scopes(source)}
    endpoints: list[JavaApiEndpointFact] = []

    for annotation_block, _visibility, method_name in METHOD_DECL_PATTERN.findall(source):
        if method_name not in method_scopes:
            continue
        for annotation_name, arguments in ANNOTATION_PATTERN.findall(annotation_block):
            http_method = HTTP_METHOD_BY_ANNOTATION.get(annotation_name)
            if annotation_name == "RequestMapping":
                http_method = _extract_request_mapping_method(arguments)
            if http_method is None:
                continue
            route = _normalize_path(base_path, _extract_route_path(arguments))
            display_name = f"{http_method} {route}"
            endpoints.append(
                JavaApiEndpointFact(
                    endpoint_key=f"api:{display_name}",
                    route=route,
                    http_method=http_method,
                    controller_module_name=controller_module_name,
                    method_name=method_name,
                )
            )
            break

    return endpoints
