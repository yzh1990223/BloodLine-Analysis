from bloodline_api.repositories import materialize_derived_flow_edges
from bloodline_api.services.graph_builder import build_table_flows


def test_build_table_flows_from_parser_shaped_step_edges():
    facts = [
        ("READS", "load_user_order_summary::table_input_1", "table:ods.orders"),
        (
            "WRITES",
            "load_user_order_summary::table_output_1",
            "table:dm.user_order_summary",
        ),
        ("READS", "refresh_daily_metrics::table_input_1", "table:ods.audit_log"),
        (
            "WRITES",
            "refresh_daily_metrics::table_output_1",
            "table:dm.audit_snapshot",
        ),
    ]

    flows = build_table_flows(facts)

    assert flows == [
        ("table:ods.audit_log", "table:dm.audit_snapshot"),
        ("table:ods.orders", "table:dm.user_order_summary"),
    ]


def test_materialize_derived_flow_edges_marks_flow_edges_as_derived():
    edges = materialize_derived_flow_edges([(1, 2)])

    assert edges[0].type == "FLOWS_TO"
    assert edges[0].src_node_id == 1
    assert edges[0].dst_node_id == 2
    assert edges[0].is_derived is True
