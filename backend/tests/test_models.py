from bloodline_api.models import Edge, Node, ObjectMetadata, ObjectMetadataColumn, ScanFailure, ScanRun


def test_models_expose_expected_tablenames():
    assert ScanRun.__tablename__ == "scan_runs"
    assert Node.__tablename__ == "nodes"
    assert Edge.__tablename__ == "edges"
    assert ObjectMetadata.__tablename__ == "object_metadata"
    assert ObjectMetadataColumn.__tablename__ == "object_metadata_columns"
    assert ScanFailure.__tablename__ == "scan_failures"


def test_object_metadata_tables_persist_latest_metadata(db_session):
    node = Node(
        type="data_object",
        key="table:dm.user_order_summary",
        name="dm.user_order_summary",
        payload={"object_type": "data_table"},
    )
    metadata = ObjectMetadata(
        node=node,
        database_name="dm",
        object_name="user_order_summary",
        object_kind="table",
        comment="summary table",
        metadata_source="mysql_information_schema",
        columns=[
            ObjectMetadataColumn(
                column_name="user_id",
                data_type="bigint",
                ordinal_position=1,
                is_nullable=False,
                column_comment="user id",
            ),
            ObjectMetadataColumn(
                column_name="order_count",
                data_type="int",
                ordinal_position=2,
                is_nullable=True,
                column_comment="orders",
            ),
        ],
    )

    db_session.add(metadata)
    db_session.commit()
    db_session.refresh(node)

    assert node.object_metadata is not None
    assert node.object_metadata.database_name == "dm"
    assert [column.column_name for column in node.object_metadata.columns] == [
        "user_id",
        "order_count",
    ]
