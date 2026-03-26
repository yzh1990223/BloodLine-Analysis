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
