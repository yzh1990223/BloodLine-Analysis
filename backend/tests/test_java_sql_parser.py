from pathlib import Path

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


def test_java_parser_extracts_static_tables_from_xml_mapper():
    parser = JavaSqlParser()
    result = parser.parse_file(Path("tests/fixtures/java_xml_mapper/OrderMapper.java"))

    assert result.read_tables == ["ods.orders"]
    assert result.write_tables == ["dm.user_order_summary"]
    assert result.methods["loadOrders"].statement_ids == ["sql_0"]
    assert result.methods["saveSummary"].statement_ids == ["sql_1"]
