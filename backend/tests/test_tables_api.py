from bloodline_api.models import Node


def test_search_tables_returns_matching_nodes(client, db_session):
    db_session.add(
        Node(type="table", key="table:ods.orders", name="ods.orders", payload={})
    )
    db_session.add(
        Node(
            type="table",
            key="table:dm.user_order_summary",
            name="dm.user_order_summary",
            payload={},
        )
    )
    db_session.commit()

    response = client.get("/api/tables/search", params={"q": "orders"})

    assert response.status_code == 200
    items = response.json()["items"]
    assert any(item["key"] == "table:ods.orders" for item in items)


def test_scan_pipeline_persists_table_lineage_and_related_objects(client):
    response = client.post(
        "/api/scan",
        json={
            "repo_path": "tests/fixtures/sample.repo.xml",
            "java_source_root": "tests/fixtures/java",
        },
    )

    assert response.status_code == 202
    assert response.json()["status"] == "completed"

    lineage = client.get("/api/tables/table:ods.orders/lineage")

    assert lineage.status_code == 200
    payload = lineage.json()
    assert payload["table"]["key"] == "table:ods.orders"
    assert any(
        item["key"] == "table:dm.user_order_summary"
        for item in payload["downstream_tables"]
    )
    assert payload["related_objects"]["jobs"][0]["name"] == "daily_summary_job"
    assert payload["related_objects"]["java_modules"][0]["name"] == "UserOrderDao"


def test_table_impact_returns_downstream_tables_and_related_objects(client):
    client.post(
        "/api/scan",
        json={
            "repo_path": "tests/fixtures/sample.repo.xml",
            "java_source_root": "tests/fixtures/java",
        },
    )

    impact = client.get("/api/tables/table:ods.orders/impact")

    assert impact.status_code == 200
    payload = impact.json()
    assert payload["table"]["key"] == "table:ods.orders"
    assert any(
        item["key"] == "table:dm.user_order_summary"
        for item in payload["downstream_tables"]
    )
    assert payload["related_objects"]["jobs"][0]["name"] == "daily_summary_job"
    assert payload["related_objects"]["java_modules"][0]["name"] == "UserOrderDao"


def test_jobs_endpoint_returns_scanned_jobs(client):
    client.post(
        "/api/scan",
        json={
            "repo_path": "tests/fixtures/sample.repo.xml",
            "java_source_root": "tests/fixtures/java",
        },
    )

    response = client.get("/api/jobs")

    assert response.status_code == 200
    assert any(item["name"] == "daily_summary_job" for item in response.json()["items"])
