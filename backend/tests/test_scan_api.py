from pathlib import Path

from bloodline_api.models import ScanFailure
from bloodline_api.models import ScanRun


def test_latest_scan_run_returns_most_recent_scan_status(client):
    response = client.get("/api/scan-runs/latest")

    assert response.status_code == 200
    assert response.json()["scan_run"] is None

    scan_response = client.post(
        "/api/scan",
        json={
            "repo_path": str(Path("tests/fixtures/sample.repo.xml")),
            "java_source_root": str(Path("tests/fixtures/java")),
        },
    )

    assert scan_response.status_code == 202

    latest_response = client.get("/api/scan-runs/latest")

    assert latest_response.status_code == 200
    body = latest_response.json()["scan_run"]
    assert body["status"] == "completed"
    assert body["id"] == scan_response.json()["scan_run_id"]
    assert body["started_at"] is not None
    assert body["finished_at"] is not None


def test_latest_scan_run_returns_saved_inputs(client):
    from bloodline_api.connectors.mysql_metadata import MySQLMetadataLoader

    original_load = MySQLMetadataLoader.load
    MySQLMetadataLoader.load = lambda self, request: []
    try:
        scan_response = client.post(
            "/api/scan",
            json={
                "repo_path": str(Path("tests/fixtures/sample.repo.xml")),
                "java_source_root": str(Path("tests/fixtures/java")),
                "mysql_dsn": "mysql+pymysql://user:pass@localhost/dm",
                "metadata_databases": ["dm", "ods"],
            },
        )
    finally:
        MySQLMetadataLoader.load = original_load

    assert scan_response.status_code == 202

    latest_response = client.get("/api/scan-runs/latest")

    assert latest_response.status_code == 200
    body = latest_response.json()["scan_run"]
    assert body["id"] == scan_response.json()["scan_run_id"]
    assert body["inputs"] == {
        "repo_path": "tests/fixtures/sample.repo.xml",
        "java_source_root": "tests/fixtures/java",
        "repo_paths": ["tests/fixtures/sample.repo.xml"],
        "java_source_roots": ["tests/fixtures/java"],
        "mysql_dsn": "mysql+pymysql://user:pass@localhost/dm",
        "metadata_databases": ["dm", "ods"],
    }


def test_latest_scan_failures_returns_file_level_groups(client, db_session):
    scan_run = ScanRun(status="completed", inputs={"java_source_root": "tests/fixtures/java"})
    db_session.add(scan_run)
    db_session.flush()
    db_session.add_all(
        [
            ScanFailure(
                scan_run_id=scan_run.id,
                source_type="java",
                file_path="tests/fixtures/java/ReportServiceImpl.java",
                failure_type="sql_parse_error",
                message="unable to parse SQL fragment",
                object_key="java_module:ReportServiceImpl",
                sql_snippet="select * from dm.user_order_summary",
            ),
            ScanFailure(
                scan_run_id=scan_run.id,
                source_type="metadata",
                file_path="dm.v_report_summary",
                failure_type="view_definition_parse_error",
                message="unsupported view definition",
                object_key="view:dm.v_report_summary",
                sql_snippet="select * from base1",
            ),
        ]
    )
    db_session.commit()

    response = client.get("/api/scan-runs/latest/failures")

    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == {
        "scan_run_id": scan_run.id,
        "failure_count": 2,
        "file_count": 2,
        "source_counts": {"kettle": 0, "java": 1, "metadata": 1},
    }
    groups = {item["source_type"]: item for item in body["groups"]}
    assert groups["java"]["files"][0]["file_path"] == "tests/fixtures/java/ReportServiceImpl.java"
    assert groups["metadata"]["files"][0]["failures"][0]["failure_type"] == "view_definition_parse_error"


def test_scan_accepts_shell_escaped_space_in_repo_path(client):
    response = client.post(
        "/api/scan",
        json={
            "repo_path": "/Users/nathan/Documents/GithubProjects/BloodLine\\ Analysis/backend/tests/fixtures/sample.repo.xml",
        },
    )

    assert response.status_code == 202
    assert response.json()["status"] == "completed"


def test_scan_accepts_metadata_database_whitelist(client):
    loaded_requests = []

    def fake_load(self, request):
        loaded_requests.append(request)
        return []

    from bloodline_api.connectors.mysql_metadata import MySQLMetadataLoader

    original_load = MySQLMetadataLoader.load
    MySQLMetadataLoader.load = fake_load
    try:
        response = client.post(
            "/api/scan",
            json={
                "repo_path": str(Path("tests/fixtures/sample.repo.xml")),
                "mysql_dsn": "mysql+pymysql://user:pass@localhost/default_db",
                "metadata_databases": ["dm", "ods"],
            },
        )
    finally:
        MySQLMetadataLoader.load = original_load

    assert response.status_code == 202
    assert response.json()["inputs"]["metadata_databases"] == ["dm", "ods"]
    assert len(loaded_requests) == 1
    assert loaded_requests[0].databases == ["dm", "ods"]


def test_scan_records_metadata_connection_failure_for_latest_summary(client):
    from bloodline_api.connectors.mysql_metadata import MySQLMetadataConnectionError
    from bloodline_api.connectors.mysql_metadata import MySQLMetadataLoader

    original_load = MySQLMetadataLoader.load
    MySQLMetadataLoader.load = lambda self, request: (_ for _ in ()).throw(
        MySQLMetadataConnectionError("MySQL 元数据连接失败，请检查 DSN、网络和账号权限后重试。(OperationalError)")
    )
    try:
        response = client.post(
            "/api/scan",
            json={
                "repo_path": str(Path("tests/fixtures/sample.repo.xml")),
                "mysql_dsn": "mysql+pymysql://user:pass@localhost/dm",
            },
        )
    finally:
        MySQLMetadataLoader.load = original_load

    assert response.status_code == 400

    failures_response = client.get("/api/scan-runs/latest/failures")
    assert failures_response.status_code == 200
    body = failures_response.json()
    assert body["summary"] == {
        "scan_run_id": body["scan_run"]["id"],
        "failure_count": 1,
        "file_count": 1,
        "source_counts": {"kettle": 0, "java": 0, "metadata": 1},
    }
    metadata_file = body["groups"][2]["files"][0]
    assert metadata_file["file_path"] == "mysql+pymysql://user:pass@localhost/dm"
    assert metadata_file["failures"][0]["failure_type"] == "MySQLMetadataConnectionError"


def test_scan_accepts_multiple_repo_and_java_paths(client):
    response = client.post(
        "/api/scan",
        json={
            "repo_paths": [
                str(Path("tests/fixtures/sample.repo.xml")),
                str(Path("tests/fixtures/repository.xml")),
            ],
            "java_source_roots": [
                str(Path("tests/fixtures/java")),
                str(Path("tests/fixtures/java_api_controller")),
            ],
        },
    )

    assert response.status_code == 202
    assert response.json()["inputs"]["repo_paths"] == [
        "tests/fixtures/sample.repo.xml",
        "tests/fixtures/repository.xml",
    ]
    assert response.json()["inputs"]["java_source_roots"] == [
        "tests/fixtures/java",
        "tests/fixtures/java_api_controller",
    ]


def test_scan_returns_friendly_error_for_invalid_repo_path(client):
    response = client.post(
        "/api/scan",
        json={
            "repo_paths": [
                "tests/fixtures/sample.repo.xml",
                "tests/fixtures/missing.repo.xml",
            ],
        },
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "第 2 个 Repo 文件路径不存在：tests/fixtures/missing.repo.xml。请检查路径后重试。"
    )


def test_scan_returns_friendly_error_for_invalid_java_directory(client):
    response = client.post(
        "/api/scan",
        json={
            "java_source_roots": [
                "tests/fixtures/java",
                "tests/fixtures/sample.repo.xml",
            ],
        },
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "第 2 个 Java 源码目录不是目录：tests/fixtures/sample.repo.xml。请填写目录路径后重试。"
    )


def test_scan_returns_friendly_error_for_mysql_metadata_connection_failure(client):
    from bloodline_api.connectors.mysql_metadata import MySQLMetadataConnectionError
    from bloodline_api.connectors.mysql_metadata import MySQLMetadataLoader

    original_load = MySQLMetadataLoader.load
    MySQLMetadataLoader.load = lambda self, request: (_ for _ in ()).throw(
        MySQLMetadataConnectionError("当前 MySQL 认证方式需要 cryptography 依赖，请先安装该依赖后再重试。")
    )
    try:
        response = client.post(
            "/api/scan",
            json={
                "mysql_dsn": "mysql+pymysql://user:pass@localhost/dm",
            },
        )
    finally:
        MySQLMetadataLoader.load = original_load

    assert response.status_code == 400
    assert "cryptography" in response.json()["detail"]
