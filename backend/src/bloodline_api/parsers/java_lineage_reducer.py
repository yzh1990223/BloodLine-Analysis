"""Reduce Java method facts back into stable table-level lineage facts."""

from __future__ import annotations

from dataclasses import dataclass

from bloodline_api.parsers.java_controller_parser import JavaApiEndpointFact
from bloodline_api.parsers.java_sql_parser import JavaMethodFact
from bloodline_api.parsers.java_sql_parser import JavaModuleParseResult
from bloodline_api.parsers.java_sql_parser import JavaSqlStatement


@dataclass(slots=True)
class ReducedJavaMethodFact:
    """Method-scoped read/write tables after following stable call edges."""

    method_name: str
    read_tables: list[str]
    write_tables: list[str]


@dataclass(slots=True)
class ReducedJavaModuleFact:
    """Module-scoped read/write tables derived from reduced method facts."""

    module_name: str
    read_tables: list[str]
    write_tables: list[str]
    methods: dict[str, ReducedJavaMethodFact]


@dataclass(slots=True)
class ReducedJavaApiEndpointFact:
    """HTTP endpoint facts reduced through the existing Java call graph."""

    endpoint_key: str
    route: str
    http_method: str
    controller_module_name: str
    method_name: str
    read_tables: list[str]
    write_tables: list[str]


def _receiver_to_module_name(receiver: str) -> str:
    """Map a lower-camel bean receiver like orderRepository to OrderRepository."""

    if not receiver:
        return receiver
    return receiver[0].upper() + receiver[1:]


def _resolve_call_target(
    modules_by_name: dict[str, JavaModuleParseResult],
    current_module_name: str,
    call: str,
) -> tuple[str, str] | None:
    """Resolve a stable local or receiver-qualified call to a module and method."""

    if "." not in call:
        module = modules_by_name.get(current_module_name)
        if module is None or call not in module.methods:
            return None
        return current_module_name, call

    receiver, callee = call.split(".", 1)
    target_module_name = _receiver_to_module_name(receiver)
    target_module = modules_by_name.get(target_module_name)
    if target_module is None or callee not in target_module.methods:
        return None
    return target_module_name, callee


def _reduce_method_tables(
    modules_by_name: dict[str, JavaModuleParseResult],
    statements_by_module: dict[str, dict[str, JavaSqlStatement]],
    module_name: str,
    method_name: str,
    cache: dict[tuple[str, str], tuple[set[str], set[str]]],
    visiting: set[tuple[str, str]],
) -> tuple[set[str], set[str]]:
    """Return one method's transitive read/write table sets."""

    key = (module_name, method_name)
    if key in cache:
        return cache[key]
    if key in visiting:
        return set(), set()

    module = modules_by_name[module_name]
    method: JavaMethodFact | None = module.methods.get(method_name)
    if method is None:
        return set(), set()

    visiting.add(key)
    reads: set[str] = set()
    writes: set[str] = set()

    statement_map = statements_by_module[module_name]
    for statement_id in method.statement_ids:
        statement = statement_map.get(statement_id)
        if statement is None:
            continue
        reads.update(statement.read_tables)
        writes.update(statement.write_tables)

    for call in method.calls:
        target = _resolve_call_target(modules_by_name, module_name, call)
        if target is None:
            continue
        target_reads, target_writes = _reduce_method_tables(
            modules_by_name,
            statements_by_module,
            target[0],
            target[1],
            cache,
            visiting,
        )
        reads.update(target_reads)
        writes.update(target_writes)

    visiting.remove(key)
    cache[key] = (reads, writes)
    return reads, writes


def reduce_java_modules(results: list[JavaModuleParseResult]) -> dict[str, ReducedJavaModuleFact]:
    """Reduce parsed Java modules into method- and module-scoped table facts."""

    modules_by_name = {result.module_name: result for result in results}
    statements_by_module = {
        result.module_name: {statement.statement_id: statement for statement in result.statements}
        for result in results
    }
    cache: dict[tuple[str, str], tuple[set[str], set[str]]] = {}
    reduced: dict[str, ReducedJavaModuleFact] = {}

    for result in results:
        reduced_methods: dict[str, ReducedJavaMethodFact] = {}
        module_reads: set[str] = set()
        module_writes: set[str] = set()
        for method_name in result.methods:
            reads, writes = _reduce_method_tables(
                modules_by_name,
                statements_by_module,
                result.module_name,
                method_name,
                cache,
                set(),
            )
            reduced_methods[method_name] = ReducedJavaMethodFact(
                method_name=method_name,
                read_tables=sorted(reads),
                write_tables=sorted(writes),
            )
            module_reads.update(reads)
            module_writes.update(writes)
        reduced[result.module_name] = ReducedJavaModuleFact(
            module_name=result.module_name,
            read_tables=sorted(module_reads),
            write_tables=sorted(module_writes),
            methods=reduced_methods,
        )

    return reduced


def reduce_java_api_endpoints(
    endpoints: list[JavaApiEndpointFact],
    reduced_modules: dict[str, ReducedJavaModuleFact],
) -> list[ReducedJavaApiEndpointFact]:
    """Reduce controller endpoints into endpoint-scoped table facts."""

    reduced: list[ReducedJavaApiEndpointFact] = []
    for endpoint in endpoints:
        module = reduced_modules.get(endpoint.controller_module_name)
        if module is None:
            continue
        method = module.methods.get(endpoint.method_name)
        if method is None:
            continue
        reduced.append(
            ReducedJavaApiEndpointFact(
                endpoint_key=endpoint.endpoint_key,
                route=endpoint.route,
                http_method=endpoint.http_method,
                controller_module_name=endpoint.controller_module_name,
                method_name=endpoint.method_name,
                read_tables=method.read_tables,
                write_tables=method.write_tables,
            )
        )
    return reduced
