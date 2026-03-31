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
