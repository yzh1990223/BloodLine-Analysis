"""Reduce Java method facts back into stable table-level lineage facts."""

from __future__ import annotations

from dataclasses import dataclass
import re

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
    resolved_call_count: int
    unresolved_call_count: int
    unresolved_reasons: list[dict[str, str]]


@dataclass(slots=True)
class JavaTypeIndex:
    """Minimal type index used to resolve interface-backed receivers."""

    interface_to_impls: dict[str, list[str]]


CRUD_METHODS = {"getById", "list", "page", "save", "updateById", "removeById"}
CRUD_READ_METHODS = {
    "selectPage",
    "selectList",
    "selectOne",
    "selectById",
    "selectBatchIds",
    "selectMaps",
    "selectCount",
}
CRUD_WRITE_METHODS = {
    "insert",
    "updateById",
    "update",
    "deleteById",
    "delete",
    "deleteBatchIds",
}
SERVICE_IMPL_PATTERN = re.compile(r"ServiceImpl<\s*([\w\.\[\]<>]+)")
IGNORED_ENDPOINT_WRAPPER_CALLS = {"Result.data", "Result.success", "Result.fail", "Result.error"}


def _receiver_to_module_name(receiver: str) -> str:
    """Map a lower-camel bean receiver like orderRepository to OrderRepository."""

    if not receiver:
        return receiver
    return receiver[0].upper() + receiver[1:]


def _normalize_type_name(type_name: str) -> str:
    """Normalize declared Java type names for stable matching."""

    type_name = re.sub(r"<.*>$", "", type_name)
    simple_name = type_name.split(".")[-1]
    simple_name = re.sub(r"\[\]$", "", simple_name)
    return simple_name


def _candidate_module_names_from_type(declared_type: str) -> list[str]:
    """Build likely implementation module names from a declared field type."""

    simple_name = _normalize_type_name(declared_type)
    candidates: list[str] = []

    def add(name: str) -> None:
        if name and name not in candidates:
            candidates.append(name)

    if simple_name.startswith("I") and len(simple_name) > 1:
        base_name = simple_name[1:]
        add(f"{base_name}Impl")
        add(base_name)

    add(f"{simple_name}Impl")
    add(simple_name)
    return candidates


def _build_type_index(results: list[JavaModuleParseResult]) -> JavaTypeIndex:
    """Build a unique interface-to-implementation lookup from parsed modules."""

    interface_to_impls: dict[str, list[str]] = {}
    for result in results:
        for implemented_type in result.implemented_types:
            normalized_type = _normalize_type_name(implemented_type)
            if not normalized_type:
                continue
            interface_to_impls.setdefault(normalized_type, []).append(result.module_name)
    return JavaTypeIndex(interface_to_impls=interface_to_impls)


def _mapper_type_from_service_impl(module: JavaModuleParseResult) -> str | None:
    """Extract the mapper type from a ServiceImpl superclass declaration when present."""

    if not module.extended_type:
        return None
    match = SERVICE_IMPL_PATTERN.search(module.extended_type)
    if match is None:
        return None
    return _normalize_type_name(match.group(1))


def _table_name_from_basemapper_module(
    module: JavaModuleParseResult,
    modules_by_name: dict[str, JavaModuleParseResult],
) -> str | None:
    """Resolve a mapper module to its entity table name via BaseMapper metadata."""

    if not module.basemapper_entity:
        return None
    entity_module = modules_by_name.get(module.basemapper_entity)
    if entity_module is None:
        return None
    return entity_module.table_name


def _crud_tables_for_module(
    module: JavaModuleParseResult,
    method_name: str,
    modules_by_name: dict[str, JavaModuleParseResult],
) -> tuple[set[str], set[str]]:
    """Derive table facts for a whitelist CRUD method when no explicit body exists."""

    table_name = _table_name_from_basemapper_module(module, modules_by_name)
    if table_name is None:
        return set(), set()
    if method_name in CRUD_READ_METHODS:
        return {table_name}, set()
    if method_name in CRUD_WRITE_METHODS:
        return set(), {table_name}
    return set(), set()


def _serviceimpl_wrapper_targets_mapper(
    module: JavaModuleParseResult,
    method_name: str,
    mapper_module: JavaModuleParseResult | None,
) -> bool:
    """Return whether a ServiceImpl wrapper method should bridge to the mapper."""

    if mapper_module is None:
        return False

    method = module.methods.get(method_name)
    if method is None:
        return False

    if method.statement_ids or "getBaseMapper" not in method.calls:
        return False
    if method_name not in mapper_module.methods:
        return False
    if not set(method.calls).issubset({"getBaseMapper", method_name}):
        return False
    return True


def _serviceimpl_crud_bridge_mapper_type(
    module: JavaModuleParseResult,
    method: JavaMethodFact | None,
) -> str | None:
    """Return the mapper module bridged by a getter-style ServiceImpl CRUD wrapper."""

    if method is None or method.statement_ids:
        return None

    mapper_type = _mapper_type_from_service_impl(module)
    if mapper_type is None:
        return None

    if method.method_name in CRUD_METHODS or method.method_name in CRUD_READ_METHODS or method.method_name in CRUD_WRITE_METHODS:
        return None
    if "getBaseMapper" not in method.calls:
        return None

    allowed_calls = {"getBaseMapper", *CRUD_READ_METHODS, *CRUD_WRITE_METHODS}
    if not method.calls or not set(method.calls).issubset(allowed_calls):
        return None
    if not any(call in CRUD_READ_METHODS or call in CRUD_WRITE_METHODS for call in method.calls):
        return None
    return mapper_type


def _serviceimpl_base_mapper_module(module: JavaModuleParseResult | None) -> str | None:
    """Return the mapper module name bound through a ServiceImpl superclass when present."""

    if module is None:
        return None
    return _mapper_type_from_service_impl(module)


def _resolve_call_target(
    modules_by_name: dict[str, JavaModuleParseResult],
    type_index: JavaTypeIndex,
    current_module_name: str,
    call: str,
) -> tuple[str, str] | None:
    """Resolve a stable local or receiver-qualified call to a module and method."""

    if "." not in call:
        module = modules_by_name.get(current_module_name)
        if module is None:
            return None
        mapper_type = _mapper_type_from_service_impl(module)
        mapper_module = None if mapper_type is None else modules_by_name.get(mapper_type)
        if _serviceimpl_wrapper_targets_mapper(module, call, mapper_module):
            return mapper_type, call  # type: ignore[return-value]
        if call not in module.methods:
            return None
        return current_module_name, call

    receiver, callee = call.split(".", 1)
    current_module = modules_by_name.get(current_module_name)
    declared_type = None if current_module is None else current_module.receiver_types.get(receiver)

    candidate_module_names: list[str] = []
    mapper_type = _serviceimpl_base_mapper_module(current_module)
    if receiver in {"baseMapper", "getBaseMapper"} and mapper_type is None:
        return None
    if declared_type is None and mapper_type is not None and receiver in {"baseMapper", "getBaseMapper"}:
        candidate_module_names.append(mapper_type)
    if declared_type:
        normalized_type = _normalize_type_name(declared_type)
        impl_candidates = type_index.interface_to_impls.get(normalized_type, [])
        if len(impl_candidates) > 1:
            return None
        if len(impl_candidates) == 1:
            candidate_module_names.extend(impl_candidates)
        candidate_module_names.extend(_candidate_module_names_from_type(declared_type))
    candidate_module_names.append(_receiver_to_module_name(receiver))

    for target_module_name in candidate_module_names:
        target_module = modules_by_name.get(target_module_name)
        if target_module is None:
            continue
        if callee not in target_module.methods:
            crud_reads, crud_writes = _crud_tables_for_module(target_module, callee, modules_by_name)
            if crud_reads or crud_writes:
                return target_module_name, callee
            if callee in CRUD_METHODS:
                mapper_type = _mapper_type_from_service_impl(target_module)
                mapper_module = None if mapper_type is None else modules_by_name.get(mapper_type)
                if mapper_module is not None and callee in mapper_module.methods:
                    return mapper_type, callee
            continue
        target_method = target_module.methods[callee]
        normalized_type = _normalize_type_name(declared_type) if declared_type else None
        if (
            declared_type
            and target_module_name == normalized_type
            and not target_method.statement_ids
            and not target_method.calls
        ):
            continue
        return target_module_name, callee
    return None


def _classify_unresolved_call(
    modules_by_name: dict[str, JavaModuleParseResult],
    type_index: JavaTypeIndex,
    current_module_name: str,
    call: str,
) -> str:
    """Return a stable unresolved reason label for one Java call."""

    if "." not in call:
        return "unresolved_local_method"

    receiver, callee = call.split(".", 1)
    current_module = modules_by_name.get(current_module_name)
    declared_type = None if current_module is None else current_module.receiver_types.get(receiver)
    if not declared_type:
        if receiver in {"baseMapper", "getBaseMapper"}:
            return "unresolved_receiver_target"
        return "unresolved_receiver_type"

    normalized_type = _normalize_type_name(declared_type)
    impl_candidates = type_index.interface_to_impls.get(normalized_type, [])
    if len(impl_candidates) > 1:
        return "multiple_impl_candidates"

    candidate_module_names = []
    if len(impl_candidates) == 1:
        candidate_module_names.extend(impl_candidates)
    candidate_module_names.extend(_candidate_module_names_from_type(declared_type))
    candidate_module_names.append(_receiver_to_module_name(receiver))

    resolved_modules = [modules_by_name.get(name) for name in candidate_module_names if modules_by_name.get(name) is not None]
    if not resolved_modules:
        return "unresolved_receiver_target"

    if not any(
        callee in module.methods
        and not (
            normalized_type == module.module_name
            and not module.methods[callee].statement_ids
            and not module.methods[callee].calls
        )
        for module in resolved_modules
    ):
        return "unresolved_target_method"

    return "unresolved_target"


def _should_ignore_endpoint_wrapper_call(call: str) -> bool:
    """Skip framework wrapper calls when summarizing endpoint diagnostics."""

    return call in IGNORED_ENDPOINT_WRAPPER_CALLS


def _reduce_method_tables(
    modules_by_name: dict[str, JavaModuleParseResult],
    statements_by_module: dict[str, dict[str, JavaSqlStatement]],
    type_index: JavaTypeIndex,
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
        return _crud_tables_for_module(module, method_name, modules_by_name)

    visiting.add(key)
    reads: set[str] = set()
    writes: set[str] = set()
    serviceimpl_crud_bridge = _serviceimpl_crud_bridge_mapper_type(module, method)

    statement_map = statements_by_module[module_name]
    for statement_id in method.statement_ids:
        statement = statement_map.get(statement_id)
        if statement is None:
            continue
        reads.update(statement.read_tables)
        writes.update(statement.write_tables)

    for call in method.calls:
        if serviceimpl_crud_bridge is not None and (call in CRUD_READ_METHODS or call in CRUD_WRITE_METHODS):
            target = (serviceimpl_crud_bridge, call)
        else:
            target = _resolve_call_target(modules_by_name, type_index, module_name, call)
        if target is None:
            continue
        target_reads, target_writes = _reduce_method_tables(
            modules_by_name,
            statements_by_module,
            type_index,
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
    type_index = _build_type_index(results)
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
                type_index,
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
    source_results: list[JavaModuleParseResult] | None = None,
) -> list[ReducedJavaApiEndpointFact]:
    """Reduce controller endpoints into endpoint-scoped table facts."""

    source_modules_by_name = {} if source_results is None else {result.module_name: result for result in source_results}
    source_type_index = JavaTypeIndex(interface_to_impls={})
    if source_results is not None:
        source_type_index = _build_type_index(source_results)

    reduced: list[ReducedJavaApiEndpointFact] = []
    for endpoint in endpoints:
        module = reduced_modules.get(endpoint.controller_module_name)
        if module is None:
            continue
        method = module.methods.get(endpoint.method_name)
        if method is None:
            continue
        source_module = source_modules_by_name.get(endpoint.controller_module_name)
        source_method = None if source_module is None else source_module.methods.get(endpoint.method_name)
        resolved_call_count = 0
        unresolved_call_count = 0
        unresolved_reasons: list[dict[str, str]] = []
        if source_method is not None:
            for call in source_method.calls:
                if _should_ignore_endpoint_wrapper_call(call):
                    continue
                if _resolve_call_target(source_modules_by_name, source_type_index, endpoint.controller_module_name, call) is None:
                    unresolved_call_count += 1
                    unresolved_reasons.append(
                        {
                            "call": call,
                            "reason": _classify_unresolved_call(
                                source_modules_by_name,
                                source_type_index,
                                endpoint.controller_module_name,
                                call,
                            ),
                        }
                    )
                else:
                    resolved_call_count += 1
        reduced.append(
            ReducedJavaApiEndpointFact(
                endpoint_key=endpoint.endpoint_key,
                route=endpoint.route,
                http_method=endpoint.http_method,
                controller_module_name=endpoint.controller_module_name,
                method_name=endpoint.method_name,
                read_tables=method.read_tables,
                write_tables=method.write_tables,
                resolved_call_count=resolved_call_count,
                unresolved_call_count=unresolved_call_count,
                unresolved_reasons=unresolved_reasons,
            )
        )
    return reduced
