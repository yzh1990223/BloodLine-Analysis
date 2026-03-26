from pathlib import Path

from bloodline_api.parsers.repo_parser import RepoParser


def test_repo_parser_extracts_kettle_io_and_calls():
    parser = RepoParser()
    result = parser.parse_file(Path("tests/fixtures/sample.repo.xml"))
    assert result.job_transformation_calls[0].job_name == "daily_summary_job"
    assert result.job_transformation_calls[0].transformation_name == "load_user_order_summary"
    assert result.jobs[0].name == "daily_summary_job"
    assert result.transformations[0].name == "load_user_order_summary"
    assert result.step_reads["load_user_order_summary::table_input_1"] == ["ods.orders"]
    assert result.step_reads["refresh_daily_metrics::table_input_1"] == ["ods.audit_log"]
    assert result.step_writes["load_user_order_summary::table_output_1"] == [
        "dm.user_order_summary"
    ]
    assert result.step_writes["refresh_daily_metrics::table_output_1"] == [
        "dm.audit_snapshot"
    ]
