from bloodline_api.connectors.mysql_metadata import MySQLMetadataConfigurationError
from bloodline_api.connectors.mysql_metadata import MySQLMetadataConnectionError
from bloodline_api.connectors.mysql_metadata import MySQLMetadataLoader
from bloodline_api.connectors.mysql_metadata import build_mysql_metadata_request


def test_mysql_metadata_request_prefers_explicit_database_whitelist():
    request = build_mysql_metadata_request(
        mysql_dsn="mysql+pymysql://user:pass@localhost/default_db",
        metadata_databases=["ods", "dm"],
    )

    assert request is not None
    assert request.databases == ["dm", "ods"]
    assert request.default_database == "default_db"


def test_mysql_metadata_request_falls_back_to_default_database():
    request = build_mysql_metadata_request(
        mysql_dsn="mysql+pymysql://user:pass@localhost/default_db",
        metadata_databases=None,
    )

    assert request is not None
    assert request.databases == ["default_db"]
    assert request.default_database == "default_db"


def test_mysql_metadata_request_requires_database_scope():
    try:
        build_mysql_metadata_request(
            mysql_dsn="mysql+pymysql://user:pass@localhost",
            metadata_databases=None,
        )
    except MySQLMetadataConfigurationError as exc:
        assert "metadata_databases" in str(exc)
    else:
        raise AssertionError("expected MySQLMetadataConfigurationError")


def test_mysql_metadata_loader_reads_tables_views_and_columns():
    request = build_mysql_metadata_request(
        mysql_dsn="mysql+pymysql://user:pass@localhost/default_db",
        metadata_databases=["dm"],
    )

    loader = MySQLMetadataLoader(
        row_fetcher=lambda _: [
            {
                "database_name": "dm",
                "object_name": "user_order_summary",
                "object_kind": "table",
                "comment": "summary table",
                "column_name": "user_id",
                "data_type": "bigint",
                "ordinal_position": 1,
                "is_nullable": "NO",
                "column_comment": "user id",
            },
            {
                "database_name": "dm",
                "object_name": "user_order_summary",
                "object_kind": "table",
                "comment": "summary table",
                "column_name": "order_count",
                "data_type": "int",
                "ordinal_position": 2,
                "is_nullable": "YES",
                "column_comment": "orders",
            },
            {
                "database_name": "dm",
                "object_name": "user_order_view",
                "object_kind": "view",
                "comment": "summary view",
                "view_definition": "select * from ods.orders",
                "column_name": "user_id",
                "data_type": "bigint",
                "ordinal_position": 1,
                "is_nullable": "YES",
                "column_comment": None,
            },
        ]
    )

    objects = loader.load(request)

    assert [item.object_name for item in objects] == [
        "user_order_summary",
        "user_order_view",
    ]
    assert objects[0].object_kind == "table"
    assert [column.column_name for column in objects[0].columns] == ["user_id", "order_count"]
    assert objects[0].columns[0].is_nullable is False
    assert objects[1].object_kind == "view"
    assert objects[1].view_definition == "select * from ods.orders"


def test_mysql_metadata_loader_returns_friendly_error_for_missing_cryptography():
    request = build_mysql_metadata_request(
        mysql_dsn="mysql+pymysql://user:pass@localhost/default_db",
        metadata_databases=["dm"],
    )

    loader = MySQLMetadataLoader(
        row_fetcher=lambda _: (_ for _ in ()).throw(
            RuntimeError("'cryptography' package is required for sha256_password or caching_sha2_password auth methods")
        )
    )

    try:
        loader.load(request)
    except MySQLMetadataConnectionError as exc:
        assert "cryptography" in str(exc)
    else:
        raise AssertionError("expected MySQLMetadataConnectionError")


def test_mysql_metadata_loader_returns_host_resolution_hint_for_invalid_hostname():
    request = build_mysql_metadata_request(
        mysql_dsn="mysql+pymysql://user:pass@localHost/default_db",
        metadata_databases=["dm"],
    )

    class FakeOperationalError(Exception):
        pass

    from sqlalchemy.exc import OperationalError

    loader = MySQLMetadataLoader(
        row_fetcher=lambda _: (_ for _ in ()).throw(
            OperationalError(
                "SELECT 1",
                {},
                FakeOperationalError("Can't connect to MySQL server on 'localHost' ([Errno 8] nodename nor servname provided, or not known)"),
            )
        )
    )

    try:
        loader.load(request)
    except MySQLMetadataConnectionError as exc:
        assert "localhost 或 127.0.0.1" in str(exc)
    else:
        raise AssertionError("expected MySQLMetadataConnectionError")
