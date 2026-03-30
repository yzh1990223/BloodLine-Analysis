from bloodline_api.connectors.mysql_metadata import MySQLMetadataConfigurationError
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
