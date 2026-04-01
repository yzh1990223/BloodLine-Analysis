from pathlib import Path
from textwrap import dedent

from bloodline_api.connectors.mysql_metadata import MySQLMetadataColumn
from bloodline_api.connectors.mysql_metadata import MySQLMetadataObject
from bloodline_api.models import Edge
from bloodline_api.models import Node
from bloodline_api.models import ObjectMetadata
from bloodline_api.models import ObjectMetadataColumn


def test_search_tables_returns_matching_nodes(client, db_session):
    orders_node = Node(
        type="data_object",
        key="table:ods.orders",
        name="ods.orders",
        payload={"object_type": "data_table"},
    )
    db_session.add(orders_node)
    db_session.flush()
    db_session.add(
        ObjectMetadata(
            node_id=orders_node.id,
            database_name="ods",
            object_name="orders",
            object_kind="table",
            comment="订单表",
            metadata_source="mysql_information_schema",
        )
    )
    db_session.add(
        Node(
            type="data_object",
            key="table:dm.user_order_summary",
            name="dm.user_order_summary",
            payload={"object_type": "data_table"},
        )
    )
    db_session.add(
        Node(
            type="api_endpoint",
            key="api:GET /api/orders/summary",
            name="GET /api/orders/summary",
            payload={"object_type": "api_endpoint", "http_method": "GET", "route": "/api/orders/summary"},
        )
    )
    db_session.commit()

    response = client.get("/api/tables/search", params={"q": "orders"})

    assert response.status_code == 200
    items = response.json()["items"]
    assert any(item["key"] == "table:ods.orders" for item in items)
    assert any(item["object_type"] == "data_table" for item in items)
    assert any(item.get("display_name") == "订单表" for item in items)

    api_response = client.get("/api/tables/search", params={"q": "orders/summary"})

    assert api_response.status_code == 200
    api_items = api_response.json()["items"]
    assert any(item["key"] == "api:GET /api/orders/summary" for item in api_items)
    assert any(item["object_type"] == "api_endpoint" for item in api_items)


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
    downstream_keys = {item["key"] for item in payload["downstream_tables"]}
    assert "table:dm.user_order_summary" in downstream_keys
    assert "table:app.order_dashboard" not in downstream_keys
    assert payload["related_objects"]["jobs"][0]["name"] == "daily_summary_job"
    assert set(payload["related_objects"]["jobs"][0]["related_table_keys"]) >= {
        "table:ods.orders",
        "table:dm.user_order_summary",
    }
    assert payload["related_objects"]["java_modules"][0]["name"] == "UserOrderDao"
    assert set(payload["related_objects"]["java_modules"][0]["related_table_keys"]) >= {
        "table:ods.orders",
        "table:dm.user_order_summary",
    }


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
    downstream_keys = {item["key"] for item in payload["downstream_tables"]}
    assert downstream_keys == {"table:dm.user_order_summary"}
    hop_by_key = {item["key"]: item["hop"] for item in payload["impacted_tables"]}
    assert hop_by_key["table:dm.user_order_summary"] == 1
    assert hop_by_key["table:app.order_dashboard"] == 2
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


def test_scan_pipeline_reduces_api_endpoint_through_interface_service_chain(client):
    response = client.post(
        "/api/scan",
        json={"java_source_root": "tests/fixtures/java_api_interface_controller"},
    )

    assert response.status_code == 202

    search_response = client.get("/api/tables/search", params={"q": "/api/report/summary"})
    assert search_response.status_code == 200
    search_items = search_response.json()["items"]
    assert any(item["key"] == "api:GET /api/report/summary" for item in search_items)

    lineage = client.get("/api/tables/table:dm.user_order_summary/lineage")
    assert lineage.status_code == 200
    api_endpoints = lineage.json()["related_objects"]["api_endpoints"]
    assert any(item["key"] == "api:GET /api/report/summary" for item in api_endpoints)


def test_scan_pipeline_reduces_api_endpoint_through_generic_interface_type(client):
    response = client.post(
        "/api/scan",
        json={"java_source_root": "tests/fixtures/java_api_generic_interface_controller"},
    )

    assert response.status_code == 202

    search_response = client.get("/api/tables/search", params={"q": "/api/generic-report/summary"})
    assert search_response.status_code == 200
    search_items = search_response.json()["items"]
    assert any(item["key"] == "api:GET /api/generic-report/summary" for item in search_items)

    lineage = client.get("/api/tables/table:dm.user_order_summary/lineage")
    assert lineage.status_code == 200
    api_endpoints = lineage.json()["related_objects"]["api_endpoints"]
    assert any(item["key"] == "api:GET /api/generic-report/summary" for item in api_endpoints)


def test_scan_pipeline_reduces_api_endpoint_through_unique_interface_impl_binding(client):
    response = client.post(
        "/api/scan",
        json={"java_source_root": "tests/fixtures/java_api_unique_impl_binding"},
    )

    assert response.status_code == 202

    search_response = client.get("/api/tables/search", params={"q": "/api/bound-report/summary"})
    assert search_response.status_code == 200
    search_items = search_response.json()["items"]
    assert any(item["key"] == "api:GET /api/bound-report/summary" for item in search_items)

    lineage = client.get("/api/tables/table:dm.user_order_summary/lineage")
    assert lineage.status_code == 200
    api_endpoints = lineage.json()["related_objects"]["api_endpoints"]
    assert any(item["key"] == "api:GET /api/bound-report/summary" for item in api_endpoints)


def test_api_endpoint_lineage_reads_tables_through_service_impl_and_mapper(client):
    response = client.post(
        "/api/scan",
        json={"java_source_root": "tests/fixtures/java_service_impl_bridge"},
    )

    assert response.status_code == 202

    payload = client.get("/api/tables/search", params={"q": "/users"})
    assert payload.status_code == 200
    api_keys = {item["key"] for item in payload.json()["items"]}
    assert "api:GET /users" in api_keys

    lineage = client.get("/api/tables/table:dm.user_info/lineage")
    assert lineage.status_code == 200
    api_endpoints = lineage.json()["related_objects"]["api_endpoints"]
    assert any(item["key"] == "api:GET /users" for item in api_endpoints)


def test_api_endpoint_payload_includes_lineage_diagnostics(client):
    client.post(
        "/api/scan",
        json={"java_source_root": "tests/fixtures/java_service_impl_bridge"},
    )

    payload = client.get("/api/tables/search", params={"q": "/users"})
    assert payload.status_code == 200
    api_item = next(item for item in payload.json()["items"] if item["key"] == "api:GET /users")
    assert api_item["payload"]["diagnostics"] == {
        "resolved_calls": 1,
        "unresolved_calls": 0,
        "unresolved_reasons": [],
        "read_table_count": 1,
        "write_table_count": 0,
    }


def test_api_endpoint_payload_reports_unresolved_reason_labels(client):
    client.post(
        "/api/scan",
        json={"java_source_root": "tests/fixtures/java_api_unresolved_diagnostics"},
    )

    payload = client.get("/api/tables/search", params={"q": "/api/diagnostic-report/summary"})
    assert payload.status_code == 200
    api_item = next(item for item in payload.json()["items"] if item["key"] == "api:GET /api/diagnostic-report/summary")
    assert api_item["payload"]["diagnostics"]["resolved_calls"] == 1
    assert api_item["payload"]["diagnostics"]["unresolved_calls"] == 1
    assert api_item["payload"]["diagnostics"]["unresolved_reasons"] == [
        {"call": "auditService.audit", "reason": "unresolved_target_method"}
    ]


def test_api_endpoint_detail_exposes_diagnostics_and_touched_tables(client):
    client.post(
        "/api/scan",
        json={"java_source_root": "tests/fixtures/java_service_impl_bridge"},
    )

    response = client.get("/api/tables/api%3AGET%20%2Fusers/connected-lineage")

    assert response.status_code == 200
    payload = response.json()["table_lineage"]
    assert payload["table"]["key"] == "api:GET /users"
    assert payload["table"]["object_type"] == "api_endpoint"
    assert payload["table"]["payload"]["diagnostics"] == {
        "resolved_calls": 1,
        "unresolved_calls": 0,
        "unresolved_reasons": [],
        "read_table_count": 1,
        "write_table_count": 0,
    }
    assert [item["key"] for item in payload["downstream_tables"]] == ["table:dm.user_info"]


def test_scan_pipeline_reduces_api_endpoint_through_unique_interface_implementation(client):
    response = client.post(
        "/api/scan",
        json={"java_source_root": "tests/fixtures/java_api_unique_impl_controller"},
    )

    assert response.status_code == 202

    search_response = client.get("/api/tables/search", params={"q": "/api/unique-report/summary"})
    assert search_response.status_code == 200
    search_items = search_response.json()["items"]
    assert any(item["key"] == "api:GET /api/unique-report/summary" for item in search_items)

    lineage = client.get("/api/tables/table:dm.user_order_summary/lineage")
    assert lineage.status_code == 200
    api_endpoints = lineage.json()["related_objects"]["api_endpoints"]
    assert any(item["key"] == "api:GET /api/unique-report/summary" for item in api_endpoints)


def test_scan_replaces_previous_graph_state(client, tmp_path):
    client.post(
        "/api/scan",
        json={
            "repo_path": "tests/fixtures/sample.repo.xml",
            "java_source_root": "tests/fixtures/java",
        },
    )

    replacement_repo = tmp_path / "replacement.repo.xml"
    replacement_repo.write_text(
        dedent(
            """
            <repository>
              <jobs>
                <job>
                  <name>replacement_job</name>
                  <transformation>replacement_transformation</transformation>
                </job>
              </jobs>
              <transformations>
                <transformation>
                  <name>replacement_transformation</name>
                  <steps>
                    <step>
                      <name>table_output_1</name>
                      <sql>insert into dm.replacement_summary select * from ods.replacement</sql>
                    </step>
                  </steps>
                </transformation>
              </transformations>
            </repository>
            """
        ).strip(),
        encoding="utf-8",
    )

    client.post("/api/scan", json={"repo_path": str(replacement_repo)})

    response = client.get("/api/tables/search", params={"q": "orders"})
    assert response.json()["items"] == []

    replacement = client.get("/api/tables/search", params={"q": "replacement"})
    assert any(item["key"] == "table:dm.replacement_summary" for item in replacement.json()["items"])


def test_table_impact_traverses_multiple_hops(client, tmp_path):
    chain_repo = tmp_path / "chain.repo.xml"
    chain_repo.write_text(
        dedent(
            """
            <repository>
              <jobs>
                <job>
                  <name>chain_job</name>
                  <transformation>stage_one</transformation>
                  <transformation>stage_two</transformation>
                  <transformation>stage_three</transformation>
                </job>
              </jobs>
              <transformations>
                <transformation>
                  <name>stage_one</name>
                  <steps>
                    <step>
                      <name>input_1</name>
                      <sql>select * from ods.source_a</sql>
                    </step>
                    <step>
                      <name>output_1</name>
                      <sql>insert into dm.stage_b select * from ods.source_a</sql>
                    </step>
                  </steps>
                </transformation>
                <transformation>
                  <name>stage_two</name>
                  <steps>
                    <step>
                      <name>input_1</name>
                      <sql>select * from dm.stage_b</sql>
                    </step>
                    <step>
                      <name>output_1</name>
                      <sql>insert into dm.stage_c select * from dm.stage_b</sql>
                    </step>
                  </steps>
                </transformation>
                <transformation>
                  <name>stage_three</name>
                  <steps>
                    <step>
                      <name>input_1</name>
                      <sql>select * from dm.stage_c</sql>
                    </step>
                    <step>
                      <name>output_1</name>
                      <sql>insert into dm.stage_d select * from dm.stage_c</sql>
                    </step>
                  </steps>
                </transformation>
              </transformations>
            </repository>
            """
        ).strip(),
        encoding="utf-8",
    )

    client.post("/api/scan", json={"repo_path": str(chain_repo)})

    response = client.get("/api/tables/table:ods.source_a/impact")

    assert response.status_code == 200
    impacted_keys = [item["key"] for item in response.json()["impacted_tables"]]
    assert impacted_keys == [
        "table:dm.stage_b",
        "table:dm.stage_c",
        "table:dm.stage_d",
    ]


def test_job_and_java_module_detail_routes_return_compact_payloads(client):
    client.post(
        "/api/scan",
        json={
            "repo_path": "tests/fixtures/sample.repo.xml",
            "java_source_root": "tests/fixtures/java",
        },
    )

    job_response = client.get("/api/jobs/job:daily_summary_job")
    java_response = client.get("/api/java-modules/java_module:UserOrderDao")

    assert job_response.status_code == 200
    assert job_response.json()["key"] == "job:daily_summary_job"
    assert job_response.json()["transformations"][0]["name"] == "load_user_order_summary"
    assert java_response.status_code == 200
    assert java_response.json()["key"] == "java_module:UserOrderDao"
    read_table_keys = {item["key"] for item in java_response.json()["read_tables"]}
    write_table_keys = {item["key"] for item in java_response.json()["write_tables"]}
    assert "table:ods.orders" in read_table_keys
    assert "table:dm.user_order_summary" in read_table_keys
    assert "table:dm.user_order_summary" in write_table_keys
    assert "table:app.order_dashboard" in write_table_keys


def test_java_module_detail_uses_call_chain_to_reduce_lineage(client):
    response = client.post(
        "/api/scan",
        json={
            "java_source_root": "tests/fixtures/java_call_chain",
        },
    )

    assert response.status_code == 202

    java_response = client.get("/api/java-modules/java_module:OrderService")

    assert java_response.status_code == 200
    read_table_keys = {item["key"] for item in java_response.json()["read_tables"]}
    write_table_keys = {item["key"] for item in java_response.json()["write_tables"]}
    assert "table:ods.orders" in read_table_keys
    assert "table:dm.user_order_summary" in write_table_keys


def test_table_lineage_includes_related_api_endpoints(client):
    response = client.post(
        "/api/scan",
        json={
            "java_source_root": "tests/fixtures/java_api_controller",
        },
    )

    assert response.status_code == 202

    lineage = client.get("/api/tables/table:dm.user_order_summary/lineage")

    assert lineage.status_code == 200
    payload = lineage.json()
    api_names = [item["name"] for item in payload["related_objects"]["api_endpoints"]]
    assert api_names == [
        "GET /api/orders/{id}",
        "POST /api/orders/summary",
    ]
    downstream_keys = {item["key"] for item in payload["downstream_tables"]}
    assert "api:GET /api/orders/{id}" in downstream_keys
    assert "api:POST /api/orders/summary" in downstream_keys


def test_scan_builds_lineage_from_view_definition(client):
    from bloodline_api.connectors.mysql_metadata import MySQLMetadataLoader

    original_load = MySQLMetadataLoader.load
    MySQLMetadataLoader.load = lambda self, request: [
        MySQLMetadataObject(
            database_name="dm",
            object_name="user_order_view",
            object_kind="view",
            comment="订单视图",
            view_definition="select * from ods.orders",
            columns=[
                MySQLMetadataColumn(
                    column_name="order_id",
                    data_type="bigint",
                    ordinal_position=1,
                    is_nullable=False,
                    column_comment=None,
                )
            ],
        )
    ]
    try:
        response = client.post(
            "/api/scan",
            json={"mysql_dsn": "mysql+pymysql://user:pass@localhost/dm"},
        )
    finally:
        MySQLMetadataLoader.load = original_load

    assert response.status_code == 202

    lineage = client.get("/api/tables/view:dm.user_order_view/lineage")

    assert lineage.status_code == 200
    payload = lineage.json()
    upstream_keys = {item["key"] for item in payload["upstream_tables"]}
    assert "table:ods.orders" in upstream_keys
    assert payload["table"]["metadata"]["view_parse_status"] == "parsed"
    assert payload["table"]["metadata"]["view_parse_error"] is None


def test_scan_keeps_failed_view_definition_visible_on_detail_page(client):
    from bloodline_api.connectors.mysql_metadata import MySQLMetadataLoader

    original_load = MySQLMetadataLoader.load
    MySQLMetadataLoader.load = lambda self, request: [
        MySQLMetadataObject(
            database_name="dm",
            object_name="broken_user_order_view",
            object_kind="view",
            comment="异常视图",
            view_definition="select * from ods.orders where id in (",
            columns=[
                MySQLMetadataColumn(
                    column_name="order_id",
                    data_type="bigint",
                    ordinal_position=1,
                    is_nullable=False,
                    column_comment=None,
                )
            ],
        )
    ]
    try:
        response = client.post(
            "/api/scan",
            json={"mysql_dsn": "mysql+pymysql://user:pass@localhost/dm"},
        )
    finally:
        MySQLMetadataLoader.load = original_load

    assert response.status_code == 202

    lineage = client.get("/api/tables/view:dm.broken_user_order_view/lineage")

    assert lineage.status_code == 200
    payload = lineage.json()
    assert payload["table"]["metadata"]["view_parse_status"] == "failed"
    assert payload["table"]["metadata"]["view_parse_error"]
    assert payload["table"]["metadata"]["view_definition"] == "select * from ods.orders where id in ("


def test_table_lineage_includes_api_endpoints_through_service_interfaces(client):
    response = client.post(
        "/api/scan",
        json={
            "java_source_root": "tests/fixtures/java_api_interface_controller",
        },
    )

    assert response.status_code == 202

    lineage = client.get("/api/tables/table:dm.user_order_summary/lineage")

    assert lineage.status_code == 200
    payload = lineage.json()
    downstream_keys = {item["key"] for item in payload["downstream_tables"]}
    assert "api:GET /api/report/summary" in downstream_keys
    api_keys = {item["key"] for item in payload["related_objects"]["api_endpoints"]}
    assert "api:GET /api/report/summary" in api_keys


def test_connected_lineage_endpoint_returns_directional_subgraph(client, db_session):
    legacy_orders = Node(
        type="data_object",
        key="source_table:legacy_orders",
        name="legacy_orders",
        payload={"object_type": "source_table"},
    )
    summary = Node(
        type="data_object",
        key="table:dm.user_order_summary",
        name="dm.user_order_summary",
        payload={"object_type": "data_table"},
    )
    dashboard = Node(
        type="data_object",
        key="table:app.order_dashboard",
        name="app.order_dashboard",
        payload={"object_type": "data_table"},
    )
    side_output = Node(
        type="data_object",
        key="table:dm.legacy_side_output",
        name="dm.legacy_side_output",
        payload={"object_type": "data_table"},
    )
    dashboard_source = Node(
        type="data_object",
        key="table:ods.dashboard_source",
        name="ods.dashboard_source",
        payload={"object_type": "data_table"},
    )
    db_session.add_all(
        [legacy_orders, summary, dashboard, side_output, dashboard_source]
    )
    db_session.flush()
    db_session.add_all(
        [
            Edge(type="FLOWS_TO", src_node_id=legacy_orders.id, dst_node_id=summary.id, is_derived=False, payload={}),
            Edge(type="FLOWS_TO", src_node_id=summary.id, dst_node_id=dashboard.id, is_derived=False, payload={}),
            Edge(type="FLOWS_TO", src_node_id=legacy_orders.id, dst_node_id=side_output.id, is_derived=False, payload={}),
            Edge(type="FLOWS_TO", src_node_id=dashboard_source.id, dst_node_id=dashboard.id, is_derived=False, payload={}),
        ]
    )
    db_session.commit()

    response = client.get("/api/tables/table:dm.user_order_summary/connected-lineage")

    assert response.status_code == 200
    payload = response.json()
    assert payload["table_lineage"]["table"]["key"] == "table:dm.user_order_summary"
    returned_keys = {item["table"]["key"] for item in payload["items"]}
    assert returned_keys == {
        "source_table:legacy_orders",
        "table:dm.user_order_summary",
        "table:app.order_dashboard",
    }
    summary_item = next(
        item for item in payload["items"] if item["table"]["key"] == "table:dm.user_order_summary"
    )
    assert [item["key"] for item in summary_item["upstream_tables"]] == ["source_table:legacy_orders"]
    assert [item["key"] for item in summary_item["downstream_tables"]] == ["table:app.order_dashboard"]


def test_scan_pipeline_persists_source_node_types_and_job_sql_objects(client, tmp_path):
    repo_path = tmp_path / "typed_sources.repo.xml"
    repo_path.write_text(
        dedent(
            """
            <repository>
              <jobs>
                <job>
                  <name>typed_job</name>
                  <entries>
                    <entry>
                      <name>cleanup</name>
                      <type>SQL</type>
                      <connection>warehouse</connection>
                      <sql>truncate table dm.cleanup_target;</sql>
                    </entry>
                    <entry>
                      <name>excel_load</name>
                      <type>TRANS</type>
                      <transname>excel_load</transname>
                    </entry>
                    <entry>
                      <name>access_load</name>
                      <type>TRANS</type>
                      <transname>access_load</transname>
                    </entry>
                  </entries>
                </job>
              </jobs>
              <transformations>
                <transformation>
                  <info>
                    <name>excel_load</name>
                  </info>
                  <step>
                    <name>Excel输入</name>
                    <type>ExcelInput</type>
                    <file>
                      <name>/data/incoming/orders.xlsx</name>
                      <filemask/>
                    </file>
                  </step>
                  <step>
                    <name>表输出</name>
                    <type>TableOutput</type>
                    <table>stg.orders_excel</table>
                  </step>
                </transformation>
                <transformation>
                  <info>
                    <name>access_load</name>
                  </info>
                  <step>
                    <name>Access 输入</name>
                    <type>AccessInput</type>
                    <table_name>legacy_orders</table_name>
                  </step>
                  <step>
                    <name>表输出</name>
                    <type>TableOutput</type>
                    <table>stg.legacy_orders</table>
                  </step>
                </transformation>
              </transformations>
            </repository>
            """
        ).strip(),
        encoding="utf-8",
    )

    response = client.post("/api/scan", json={"repo_path": str(repo_path)})

    assert response.status_code == 202

    file_search = client.get("/api/tables/search", params={"q": "orders.xlsx"})
    source_file = file_search.json()["items"][0]
    assert source_file["object_type"] == "source_file"

    source_table_search = client.get("/api/tables/search", params={"q": "legacy_orders"})
    source_table = next(
        item for item in source_table_search.json()["items"] if item["object_type"] == "source_table"
    )
    assert source_table["name"] == "legacy_orders"

    cleanup_search = client.get("/api/tables/search", params={"q": "cleanup_target"})
    assert cleanup_search.json()["items"][0]["object_type"] == "data_table"

    lineage = client.get("/api/tables/table:stg.orders_excel/lineage")
    assert lineage.status_code == 200
    assert lineage.json()["upstream_tables"][0]["object_type"] == "source_file"


def test_scan_pipeline_merges_mysql_metadata_into_table_and_view_nodes(client, db_session, monkeypatch):
    def fake_load(self, request):
        assert request.databases == ["winddf"]
        return [
            MySQLMetadataObject(
                database_name="winddf",
                object_name="cbonddescription",
                object_kind="table",
                comment="bond base table",
                view_definition=None,
                columns=[
                    MySQLMetadataColumn(
                        column_name="bond_code",
                        data_type="varchar",
                        ordinal_position=1,
                        is_nullable=False,
                        column_comment="债券代码",
                    )
                ],
            ),
            MySQLMetadataObject(
                database_name="winddf",
                object_name="cbond_view",
                object_kind="view",
                comment="bond view",
                view_definition="select * from winddf.cbonddescription",
                columns=[
                    MySQLMetadataColumn(
                        column_name="bond_name",
                        data_type="varchar",
                        ordinal_position=1,
                        is_nullable=True,
                        column_comment="债券名称",
                    )
                ],
            ),
        ]

    monkeypatch.setattr(
        "bloodline_api.connectors.mysql_metadata.MySQLMetadataLoader.load",
        fake_load,
    )

    response = client.post(
        "/api/scan",
        json={
            "repo_path": "tests/fixtures/sample.repo.xml",
            "mysql_dsn": "mysql+pymysql://user:pass@localhost/winddf",
            "metadata_databases": ["winddf"],
        },
    )

    assert response.status_code == 202

    table_node = db_session.query(Node).filter(Node.key == "table:winddf.cbonddescription").one_or_none()
    assert table_node is not None
    assert table_node.payload["object_type"] == "data_table"

    view_node = db_session.query(Node).filter(Node.key == "view:winddf.cbond_view").one_or_none()
    assert view_node is not None
    assert view_node.payload["object_type"] == "table_view"

    metadata = db_session.query(ObjectMetadata).filter(ObjectMetadata.node_id == table_node.id).one_or_none()
    assert metadata is not None
    assert metadata.database_name == "winddf"
    assert metadata.object_name == "cbonddescription"
    assert metadata.object_kind == "table"
    assert metadata.metadata_source == "mysql_information_schema"
    assert [column.column_name for column in metadata.columns] == ["bond_code"]

    detail = client.get("/api/tables/table:winddf.cbonddescription/lineage")
    assert detail.status_code == 200
    assert detail.json()["table"]["metadata"] == {
        "database_name": "winddf",
        "object_name": "cbonddescription",
        "object_kind": "table",
        "comment": "bond base table",
        "column_count": 1,
        "view_definition": None,
        "view_parse_status": "not_applicable",
        "view_parse_error": None,
        "metadata_source": "mysql_information_schema",
    }


def test_scan_pipeline_reuses_metadata_node_for_bare_repo_table_names(client, monkeypatch, tmp_path):
    def fake_load(self, request):
        return [
            MySQLMetadataObject(
                database_name="winddf",
                object_name="cbonddescription",
                object_kind="table",
                comment="bond base table",
                view_definition=None,
                columns=[
                    MySQLMetadataColumn(
                        column_name="bond_code",
                        data_type="varchar",
                        ordinal_position=1,
                        is_nullable=False,
                        column_comment=None,
                    )
                ],
            )
        ]

    monkeypatch.setattr(
        "bloodline_api.connectors.mysql_metadata.MySQLMetadataLoader.load",
        fake_load,
    )

    repo_path = tmp_path / "metadata_merge.repo.xml"
    repo_path.write_text(
        dedent(
            """
            <repository>
              <jobs>
                <job>
                  <name>metadata_job</name>
                  <transformation>metadata_transformation</transformation>
                </job>
              </jobs>
              <transformations>
                <transformation>
                  <name>metadata_transformation</name>
                  <steps>
                    <step>
                      <name>input_1</name>
                      <sql>select * from cbonddescription</sql>
                    </step>
                    <step>
                      <name>output_1</name>
                      <sql>insert into dm.metadata_target select * from cbonddescription</sql>
                    </step>
                  </steps>
                </transformation>
              </transformations>
            </repository>
            """
        ).strip(),
        encoding="utf-8",
    )

    response = client.post(
        "/api/scan",
        json={
            "repo_path": str(repo_path),
            "mysql_dsn": "mysql+pymysql://user:pass@localhost/winddf",
        },
    )

    assert response.status_code == 202

    search = client.get("/api/tables/search", params={"q": "cbonddescription"})
    keys = {item["key"] for item in search.json()["items"]}
    assert "table:winddf.cbonddescription" in keys
    assert "table:cbonddescription" not in keys

    lineage = client.get("/api/tables/table:dm.metadata_target/lineage")
    assert lineage.status_code == 200
    upstream_keys = {item["key"] for item in lineage.json()["upstream_tables"]}
    assert "table:winddf.cbonddescription" in upstream_keys


def test_rescan_without_mysql_metadata_clears_metadata_tables(client, db_session, monkeypatch, tmp_path):
    def fake_load(self, request):
        return [
            MySQLMetadataObject(
                database_name="winddf",
                object_name="cbonddescription",
                object_kind="table",
                comment="bond base table",
                view_definition=None,
                columns=[
                    MySQLMetadataColumn(
                        column_name="bond_code",
                        data_type="varchar",
                        ordinal_position=1,
                        is_nullable=False,
                        column_comment=None,
                    )
                ],
            )
        ]

    monkeypatch.setattr(
        "bloodline_api.connectors.mysql_metadata.MySQLMetadataLoader.load",
        fake_load,
    )

    first_response = client.post(
        "/api/scan",
        json={
            "repo_path": "tests/fixtures/sample.repo.xml",
            "mysql_dsn": "mysql+pymysql://user:pass@localhost/winddf",
        },
    )
    assert first_response.status_code == 202
    assert db_session.query(ObjectMetadata).count() == 1
    assert db_session.query(ObjectMetadataColumn).count() == 1

    replacement_repo = tmp_path / "replacement.repo.xml"
    replacement_repo.write_text(
        dedent(
            """
            <repository>
              <transformations>
                <transformation>
                  <name>replacement_transformation</name>
                  <steps>
                    <step>
                      <name>output_1</name>
                      <sql>insert into dm.replacement_summary select * from ods.replacement</sql>
                    </step>
                  </steps>
                </transformation>
              </transformations>
            </repository>
            """
        ).strip(),
        encoding="utf-8",
    )

    second_response = client.post("/api/scan", json={"repo_path": str(replacement_repo)})
    assert second_response.status_code == 202
    assert db_session.query(ObjectMetadata).count() == 0
    assert db_session.query(ObjectMetadataColumn).count() == 0


def test_cycle_group_summary_returns_multi_table_closed_loops(client, db_session):
    loop_left = Node(
        type="data_object",
        key="table:dm.loop_left",
        name="dm.loop_left",
        payload={"object_type": "data_table"},
    )
    loop_right = Node(
        type="data_object",
        key="table:dm.loop_right",
        name="dm.loop_right",
        payload={"object_type": "data_table"},
    )
    triangle_a = Node(
        type="data_object",
        key="table:dm.triangle_a",
        name="dm.triangle_a",
        payload={"object_type": "data_table"},
    )
    triangle_b = Node(
        type="data_object",
        key="table:dm.triangle_b",
        name="dm.triangle_b",
        payload={"object_type": "data_table"},
    )
    triangle_c = Node(
        type="data_object",
        key="table:dm.triangle_c",
        name="dm.triangle_c",
        payload={"object_type": "data_table"},
    )
    self_loop_only = Node(
        type="data_object",
        key="table:dm.self_only",
        name="dm.self_only",
        payload={"object_type": "data_table"},
    )
    db_session.add_all([loop_left, loop_right, triangle_a, triangle_b, triangle_c, self_loop_only])
    db_session.flush()
    db_session.add_all(
        [
            Edge(type="FLOWS_TO", src_node_id=loop_left.id, dst_node_id=loop_right.id, is_derived=True, payload={}),
            Edge(type="FLOWS_TO", src_node_id=loop_right.id, dst_node_id=loop_left.id, is_derived=True, payload={}),
            Edge(type="FLOWS_TO", src_node_id=triangle_a.id, dst_node_id=triangle_b.id, is_derived=True, payload={}),
            Edge(type="FLOWS_TO", src_node_id=triangle_b.id, dst_node_id=triangle_c.id, is_derived=True, payload={}),
            Edge(type="FLOWS_TO", src_node_id=triangle_c.id, dst_node_id=triangle_a.id, is_derived=True, payload={}),
            Edge(type="FLOWS_TO", src_node_id=triangle_a.id, dst_node_id=triangle_c.id, is_derived=True, payload={}),
            Edge(type="FLOWS_TO", src_node_id=self_loop_only.id, dst_node_id=self_loop_only.id, is_derived=True, payload={}),
        ]
    )
    db_session.commit()

    response = client.get("/api/analysis/cycles")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"] == {"group_count": 2, "table_count": 5, "edge_count": 6}
    assert payload["items"][0]["group_key"] == "cycle_group:1"
    assert payload["items"][0]["table_count"] == 3
    assert payload["items"][0]["edge_count"] == 4
    assert payload["items"][0]["tables"] == [
        {
            "id": triangle_a.id,
            "key": "table:dm.triangle_a",
            "name": "dm.triangle_a",
            "display_name": "dm.triangle_a",
            "object_type": "data_table",
            "payload": {"object_type": "data_table"},
            "cycle_edge_count": 3,
        },
        {
            "id": triangle_c.id,
            "key": "table:dm.triangle_c",
            "name": "dm.triangle_c",
            "display_name": "dm.triangle_c",
            "object_type": "data_table",
            "payload": {"object_type": "data_table"},
            "cycle_edge_count": 3,
        },
        {
            "id": triangle_b.id,
            "key": "table:dm.triangle_b",
            "name": "dm.triangle_b",
            "display_name": "dm.triangle_b",
            "object_type": "data_table",
            "payload": {"object_type": "data_table"},
            "cycle_edge_count": 2,
        },
    ]
    assert payload["items"][1]["group_key"] == "cycle_group:2"
    assert payload["items"][1]["table_count"] == 2
    assert payload["items"][1]["edge_count"] == 2
    assert payload["items"][1]["tables"] == [
        {
            "id": loop_left.id,
            "key": "table:dm.loop_left",
            "name": "dm.loop_left",
            "display_name": "dm.loop_left",
            "object_type": "data_table",
            "payload": {"object_type": "data_table"},
            "cycle_edge_count": 2,
        },
        {
            "id": loop_right.id,
            "key": "table:dm.loop_right",
            "name": "dm.loop_right",
            "display_name": "dm.loop_right",
            "object_type": "data_table",
            "payload": {"object_type": "data_table"},
            "cycle_edge_count": 2,
        },
    ]
