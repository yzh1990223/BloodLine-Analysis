from pathlib import Path


def test_end_to_end_sample_scan_builds_multi_hop_lineage(client):
    response = client.post(
        "/api/scan",
        json={
            "repo_path": str(Path("tests/fixtures/sample.repo.xml")),
            "java_source_root": str(Path("tests/fixtures/java")),
        },
    )

    assert response.status_code == 202

    lineage = client.get("/api/tables/table:dm.user_order_summary/lineage")
    assert lineage.status_code == 200
    lineage_body = lineage.json()
    assert lineage_body["table"]["key"] == "table:dm.user_order_summary"
    assert any(
        table["key"] == "table:ods.orders"
        for table in lineage_body["upstream_tables"]
    )

    impact = client.get("/api/tables/table:ods.orders/impact")
    assert impact.status_code == 200
    impacted_tables = impact.json()["impacted_tables"]
    impacted_keys = {table["key"] for table in impacted_tables}
    assert "table:dm.user_order_summary" in impacted_keys
    assert "table:app.order_dashboard" in impacted_keys
