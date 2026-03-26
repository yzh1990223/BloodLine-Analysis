from bloodline_api.models import Edge, Node, ScanRun


def test_models_expose_expected_tablenames():
    assert ScanRun.__tablename__ == "scan_runs"
    assert Node.__tablename__ == "nodes"
    assert Edge.__tablename__ == "edges"
