from pathlib import Path
from textwrap import dedent

from bloodline_api.models import Node


def test_search_tables_returns_matching_nodes(client, db_session):
    db_session.add(
        Node(
            type="data_object",
            key="table:ods.orders",
            name="ods.orders",
            payload={"object_type": "data_table"},
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
    db_session.commit()

    response = client.get("/api/tables/search", params={"q": "orders"})

    assert response.status_code == 200
    items = response.json()["items"]
    assert any(item["key"] == "table:ods.orders" for item in items)
    assert any(item["object_type"] == "data_table" for item in items)


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
