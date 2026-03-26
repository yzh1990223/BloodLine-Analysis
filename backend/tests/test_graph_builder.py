from bloodline_api.services.graph_builder import build_table_flows


def test_build_table_flows_from_fact_edges():
    facts = [
        ("READS", "step:table_input_1", "table:ods.orders"),
        ("WRITES", "step:table_output_1", "table:dm.user_order_summary"),
    ]

    flows = build_table_flows(facts)

    assert flows == [("table:ods.orders", "table:dm.user_order_summary")]
