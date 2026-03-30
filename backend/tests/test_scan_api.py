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
    response = client.post(
        "/api/scan",
        json={
            "repo_path": str(Path("tests/fixtures/sample.repo.xml")),
            "mysql_dsn": "mysql+pymysql://user:pass@localhost/default_db",
            "metadata_databases": ["dm", "ods"],
        },
    )

    assert response.status_code == 202
    assert response.json()["inputs"]["metadata_databases"] == ["dm", "ods"]
