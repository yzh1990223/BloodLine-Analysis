from pathlib import Path


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
