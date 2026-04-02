from pathlib import Path

from bloodline_api.connectors.java_source_reader import read_java_source
from bloodline_api.parsers.java_symbol_parser import parse_field_types
from bloodline_api.parsers.java_symbol_parser import parse_implemented_types
from bloodline_api.parsers.java_controller_parser import parse_controller_endpoints
from bloodline_api.parsers.java_sql_parser import JavaSqlParser
from bloodline_api.parsers.sql_table_extractor import extract_tables


def test_java_sql_parser_extracts_reads_and_writes():
    parser = JavaSqlParser()
    result = parser.parse_file(Path("tests/fixtures/java/UserOrderDao.java"))
    assert result.module_name == "UserOrderDao"
    assert sorted(result.read_tables) == ["dm.user_order_summary", "ods.orders"]
    assert sorted(result.write_tables) == ["app.order_dashboard", "dm.user_order_summary"]
    assert [
        (statement.read_tables, statement.write_tables) for statement in result.statements
    ] == [
        (["ods.orders"], []),
        (["ods.orders"], ["dm.user_order_summary"]),
        (["dm.user_order_summary"], ["app.order_dashboard"]),
    ]


def test_extract_tables_normalizes_aliased_reads():
    reads, writes = extract_tables(
        "select * from ods.orders o join dm.dim_user u on o.user_id = u.id"
    )
    assert reads == {"ods.orders", "dm.dim_user"}
    assert writes == set()


def test_extract_tables_returns_empty_for_unstable_dynamic_mybatis_sql():
    reads, writes = extract_tables(
        "select id from ods.orders where ch_type in ('1', '2', '3') 0\"> and r.id in #{item}"
    )

    assert reads == set()
    assert writes == set()


def test_extract_tables_excludes_cte_aliases_but_keeps_underlying_tables():
    reads, writes = extract_tables(
        """
        WITH base AS (
            SELECT * FROM ods.orders
        ),
        base1 AS (
            SELECT * FROM dm.dim_user
        ),
        base2 AS (
            SELECT *
            FROM base
            JOIN base1 ON base.user_id = base1.id
        )
        SELECT * FROM base2
        """
    )

    assert reads == {"dm.dim_user", "ods.orders"}
    assert writes == set()


def test_java_parser_emits_method_scoped_statement_facts():
    parser = JavaSqlParser()
    result = parser.parse_file(Path("tests/fixtures/java_method_model/OrderService.java"))

    assert result.methods["syncOrderSummary"].statement_ids == ["sql_0"]
    assert "execute" in result.methods["syncOrderSummary"].calls
    assert "orderRepository.saveSummary" in result.methods["syncOrderSummary"].calls


def test_java_parser_tracks_simple_service_to_repository_calls():
    parser = JavaSqlParser()
    result = parser.parse_file(Path("tests/fixtures/java_method_model/OrderService.java"))

    assert result.methods["syncOrderSummary"].calls == [
        "orderRepository.saveSummary",
        "execute",
    ]


def test_java_parser_extracts_tables_from_mybatis_annotations():
    parser = JavaSqlParser()
    result = parser.parse_file(Path("tests/fixtures/java_annotation_model/AnnotatedMapper.java"))

    assert result.read_tables == ["ods.orders"]
    assert result.write_tables == ["dm.user_order_summary"]
    assert result.methods["loadOrders"].statement_ids == ["sql_0"]
    assert result.methods["saveSummary"].statement_ids == ["sql_1"]


def test_java_parser_extracts_tables_from_value_style_mybatis_annotations():
    parser = JavaSqlParser()
    result = parser.parse_file(Path("tests/fixtures/java_annotation_value_model/ValueAnnotatedMapper.java"))

    assert result.read_tables == ["ods.orders"]
    assert result.write_tables == []
    assert result.methods["loadOrders"].statement_ids == ["sql_0"]


def test_java_parser_extracts_tables_from_concatenated_annotation_sql():
    parser = JavaSqlParser()
    result = parser.parse_file(Path("tests/fixtures/java_annotation_concat_model/ConcatAnnotatedMapper.java"))

    assert result.read_tables == ["ods.orders"]
    assert result.write_tables == ["dm.user_order_summary"]
    assert result.methods["loadOrders"].statement_ids == ["sql_0"]
    assert result.methods["saveSummary"].statement_ids == ["sql_1"]


def test_java_parser_extracts_static_tables_from_xml_mapper():
    parser = JavaSqlParser()
    result = parser.parse_file(Path("tests/fixtures/java_xml_mapper/OrderMapper.java"))

    assert result.read_tables == ["ods.orders"]
    assert result.write_tables == ["dm.user_order_summary"]
    assert result.methods["loadOrders"].statement_ids == ["sql_0"]
    assert result.methods["saveSummary"].statement_ids == ["sql_1"]


def test_java_parser_extracts_tables_from_resources_mapper_layout():
    parser = JavaSqlParser()
    result = parser.parse_file(Path("tests/fixtures/java_mapper_resources/OrderMapper.java"))

    assert result.read_tables == ["ods.orders"]
    assert result.write_tables == []
    assert result.methods["loadOrders"].statement_ids == ["sql_0"]


def test_java_parser_normalizes_where_blocks_and_placeholders_from_xml_mapper():
    parser = JavaSqlParser()
    result = parser.parse_file(Path("tests/fixtures/java_xml_where_mapper/PressureMapper.java"))

    assert result.read_tables == ["RM_PRESSURE_RESULT"]
    assert result.write_tables == []
    assert result.methods["loadByExecId"].statement_ids == ["sql_0"]


def test_java_parser_skips_unstable_dynamic_xml_mapper_sql():
    parser = JavaSqlParser()
    result = parser.parse_file(Path("tests/fixtures/java_dynamic_xml_mapper/DynamicMapper.java"))

    assert result.read_tables == []
    assert result.write_tables == []
    assert result.statements == []
    assert result.methods["findIds"].statement_ids == []


def test_java_symbol_parser_extracts_controller_field_types():
    source = read_java_source(Path("tests/fixtures/java_api_interface_controller/ReportController.java"))

    assert parse_field_types(source) == {"reportService": "IReportService"}


def test_java_symbol_parser_preserves_generic_controller_field_types():
    source = read_java_source(
        Path("tests/fixtures/java_api_generic_interface_controller/GenericReportController.java")
    )

    assert parse_field_types(source) == {"reportService": "IReportService<ReportRow>"}


def test_java_symbol_parser_extracts_implemented_generic_interfaces():
    source = read_java_source(
        Path("tests/fixtures/java_api_generic_interface_controller/ReportServiceImpl.java")
    )

    assert parse_implemented_types(source) == ["IReportService"]


def test_java_lineage_reducer_strips_generic_qualifiers_from_declared_types():
    from bloodline_api.parsers.java_lineage_reducer import _candidate_module_names_from_type

    assert _candidate_module_names_from_type("com.demo.IReportService<com.demo.ReportRow>") == [
        "ReportServiceImpl",
        "ReportService",
        "IReportServiceImpl",
        "IReportService",
    ]


def test_java_symbol_parser_extracts_normalized_implemented_types():
    from bloodline_api.parsers.java_symbol_parser import parse_implemented_types

    source = read_java_source(
        Path("tests/fixtures/java_api_unique_impl_binding/DailyReportAdapter.java")
    )

    assert parse_implemented_types(source) == ["IReportService"]


def test_java_symbol_parser_extracts_serviceimpl_superclass():
    from bloodline_api.parsers.java_symbol_parser import parse_extended_type

    source = read_java_source(Path("tests/fixtures/java_service_impl_bridge/UserServiceImpl.java"))

    assert parse_extended_type(source) == "ServiceImpl<UserMapper, UserEntity>"


def test_java_controller_parser_extracts_http_endpoint_facts():
    endpoints = parse_controller_endpoints(
        Path("tests/fixtures/java_api_controller/OrderSummaryController.java")
    )

    assert [(item.http_method, item.route, item.method_name) for item in endpoints] == [
        ("GET", "/api/orders/{id}", "getSummary"),
        ("POST", "/api/orders/summary", "refreshSummary"),
    ]
    assert [item.endpoint_key for item in endpoints] == [
        "api:GET /api/orders/{id}",
        "api:POST /api/orders/summary",
    ]


def test_java_controller_parser_handles_generic_return_types():
    endpoints = parse_controller_endpoints(
        Path("tests/fixtures/java_api_interface_controller/AssetManagementNetWorthController.java")
    )

    assert [(item.http_method, item.route, item.method_name) for item in endpoints] == [
        ("GET", "/assetManagement/selectAssetManagementNetWorth", "selectAssetManagementNetWorth"),
        ("GET", "/assetManagement/calculate", "calculate"),
    ]
