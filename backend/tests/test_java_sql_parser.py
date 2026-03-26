from pathlib import Path

from bloodline_api.parsers.java_sql_parser import JavaSqlParser
from bloodline_api.parsers.sql_table_extractor import extract_tables


def test_java_sql_parser_extracts_reads_and_writes():
    parser = JavaSqlParser()
    result = parser.parse_file(Path("tests/fixtures/java/UserOrderDao.java"))
    assert result.module_name == "UserOrderDao"
    assert sorted(result.read_tables) == ["ods.orders"]
    assert sorted(result.write_tables) == ["dm.user_order_summary"]


def test_extract_tables_normalizes_aliased_reads():
    reads, writes = extract_tables(
        "select * from ods.orders o join dm.dim_user u on o.user_id = u.id"
    )
    assert reads == {"ods.orders", "dm.dim_user"}
    assert writes == set()
