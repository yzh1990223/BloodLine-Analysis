from pathlib import Path

from bloodline_api.parsers.java_sql_parser import JavaSqlParser


def test_java_sql_parser_extracts_reads_and_writes():
    parser = JavaSqlParser()
    result = parser.parse_file(Path("tests/fixtures/java/UserOrderDao.java"))
    assert result.module_name == "UserOrderDao"
    assert sorted(result.read_tables) == ["ods.orders"]
    assert sorted(result.write_tables) == ["dm.user_order_summary"]
