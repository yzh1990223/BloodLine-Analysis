from pathlib import Path

from bloodline_api.parsers.repo_parser import RepoParser


def test_repo_parser_extracts_kettle_io_and_calls():
    parser = RepoParser()
    result = parser.parse_file(Path("tests/fixtures/sample.repo.xml"))
    assert result.job_transformation_calls[0].job_name == "daily_summary_job"
    assert result.job_transformation_calls[0].transformation_name == "load_user_order_summary"
    assert result.jobs[0].name == "daily_summary_job"
    assert result.transformations[0].name == "load_user_order_summary"
    assert [item.name for item in result.step_reads["load_user_order_summary::table_input_1"]] == [
        "ods.orders"
    ]
    assert [item.object_type for item in result.step_reads["load_user_order_summary::table_input_1"]] == [
        "data_table"
    ]
    assert [item.name for item in result.step_reads["refresh_daily_metrics::table_input_1"]] == [
        "ods.audit_log"
    ]
    assert [item.name for item in result.step_writes["load_user_order_summary::table_output_1"]] == [
        "dm.user_order_summary"
    ]
    assert [item.name for item in result.step_writes["refresh_daily_metrics::table_output_1"]] == [
        "dm.audit_snapshot"
    ]


def test_repo_parser_supports_real_repository_export_layout_and_database_steps():
    parser = RepoParser()
    result = parser.parse_file(Path("tests/fixtures/repository.xml"))

    job_calls = {
        (call.job_name, call.transformation_name) for call in result.job_transformation_calls
    }

    assert ("CHINADAAS_ENTITYINFO", "CHINADAAS_ENTITYINFO") in job_calls
    assert ("FI_HK_ACCESS_4", "RM_LOAD_DATA_TIME_LOG") in job_calls
    assert any(item.name == "CHINADAAS_ENTITYINFO" for item in result.transformations)
    assert any(item.name == "ACCESS_TEST" for item in result.transformations)
    assert [item.name for item in result.step_reads["CHINADAAS_ENTITYINFO::表输入"]] == [
        "dc_client_original"
    ]
    assert [item.name for item in result.step_writes["CHINADAAS_ENTITYINFO::插入 / 更新"]] == [
        "chinadaas_entinfo"
    ]
    access_reads = result.step_reads["ACCESS_TEST::0_BondFtOptPosition_HK"]
    assert [item.name for item in access_reads] == ["0_bondftoptposition_hk"]
    assert [item.object_type for item in access_reads] == ["data_table"]
    assert [item.name for item in result.step_writes["ACCESS_TEST::表输出"]] == [
        "rp_xs_risk_0_bondftoptposition_hk"
    ]
    assert [item.name for item in result.step_writes["frms_si_snowball_cc::DELETE_OLD_DATA"]] == [
        "ods.si_snowball_cc"
    ]


def test_repo_parser_extracts_job_sql_and_file_inputs():
    parser = RepoParser()
    result = parser.parse_file(Path("tests/fixtures/repository.xml"))

    assert [item.name for item in result.job_writes["FI_RM_DEPOSIT::清除当天数据"]] == [
        "rp_fi_rm_deposit"
    ]
    assert [item.object_type for item in result.job_writes["FI_RM_DEPOSIT::清除当天数据"]] == [
        "data_table"
    ]
    excel_reads = result.step_reads["frms_si_snowball_cc::Excel输入"]
    assert [item.object_type for item in excel_reads] == ["source_file"]
