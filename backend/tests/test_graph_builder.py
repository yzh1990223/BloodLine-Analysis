from bloodline_api.services.graph_builder import build_table_flows


def test_build_table_flows_from_fact_edges():
    facts = [
        ("READS", "job:daily_summary", "table:ods.orders"),
        ("WRITES", "job:daily_summary", "table:dm.user_order_summary"),
        ("READS", "job:refresh_metrics", "table:ods.audit_log"),
        ("WRITES", "job:refresh_metrics", "table:dm.audit_snapshot"),
    ]

    flows = build_table_flows(facts)

    assert flows == [
        ("table:ods.audit_log", "table:dm.audit_snapshot"),
        ("table:ods.orders", "table:dm.user_order_summary"),
    ]
