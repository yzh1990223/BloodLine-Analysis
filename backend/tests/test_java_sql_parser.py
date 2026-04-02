from pathlib import Path

from bloodline_api.connectors.java_source_reader import read_java_source
from bloodline_api.parsers.java_symbol_parser import parse_basemapper_entity
from bloodline_api.parsers.java_symbol_parser import parse_field_types
from bloodline_api.parsers.java_symbol_parser import parse_implemented_types
from bloodline_api.parsers.java_symbol_parser import parse_table_name
from bloodline_api.parsers.java_controller_parser import parse_controller_endpoints
from bloodline_api.parsers.java_sql_parser import JavaSqlParser
from bloodline_api.parsers.sql_table_extractor import extract_tables


def test_java_sql_parser_extracts_reads_and_writes():
    parser = JavaSqlParser()
    result = parser.parse_file(Path("tests/fixtures/java/UserOrderDao.java"))
    assert result.module_name == "UserOrderDao"
    assert sorted(result.read_tables) == ["dm.user_order_summary", "ods.orders"]
    assert sorted(result.write_tables) == ["app.order_dashboard", "dm.user_order_summary"]
    assert [
        (statement.read_tables, statement.write_tables) for statement in result.statements
    ] == [
        (["ods.orders"], []),
        (["ods.orders"], ["dm.user_order_summary"]),
        (["dm.user_order_summary"], ["app.order_dashboard"]),
    ]


def test_java_parser_decodes_escaped_newlines_in_plain_sql_strings():
    parser = JavaSqlParser()
    result = parser.parse_file(Path("tests/fixtures/java_string_escaped_model/EscapedSqlDao.java"))

    assert result.read_tables == ["ods.orders"]
    assert result.write_tables == []
    assert result.methods["loadOrders"].statement_ids == ["sql_0"]


def test_extract_tables_tolerates_backslash_line_continuations():
    reads, writes = extract_tables(
        "select * from ods.orders \\\nwhere id = 1"
    )

    assert reads == {"ods.orders"}
    assert writes == set()


def test_extract_tables_preserves_sql_after_leading_line_comments():
    reads, writes = extract_tables(
        """
        --select *  from V_CICC_BIGCOMPANY_BASIC T WHERE  dpt_count>0
        --and t.industry is null
        SELECT A.CLIENT_ID as COMPANY_ID,A.CLIENT_NAME as COMPANY_FULL_NAME
          FROM DC_CLIENT_ORIGINAL A
         WHERE A.ORGAN_FLAG = '2'
        """
    )

    assert reads == {"DC_CLIENT_ORIGINAL"}
    assert writes == set()


def test_extract_tables_strips_inline_sql_comments_inside_select_list():
    reads, writes = extract_tables(
        """
        select tt.* from (
            select a.CLIENT_ID as clientId --客户ID
                 , a.SYSTEM_ID as systemId --系统ID
            from RM_CLIENT_INFO a
        ) tt
        """
    )

    assert reads == {"RM_CLIENT_INFO"}
    assert writes == set()


def test_extract_tables_strips_inline_comment_after_string_literal():
    reads, writes = extract_tables(
        """
        select * from RM_PB_CLIENT_INDEN t
        where PBTYPE2 = 'INTBL'--同业互借
          and t.counterpartyname = '浦成QDII普通A'
        """
    )

    assert reads == {"RM_PB_CLIENT_INDEN"}
    assert writes == set()


def test_extract_tables_normalizes_aliased_reads():
    reads, writes = extract_tables(
        "select * from ods.orders o join dm.dim_user u on o.user_id = u.id"
    )
    assert reads == {"ods.orders", "dm.dim_user"}
    assert writes == set()


def test_extract_tables_normalizes_where_and_after_dynamic_fragment_removal():
    reads, writes = extract_tables(
        "select * from RM_CALL_MARGIN_PAY_LOG t WHERE AND t.CLIENT_NAME like 'abc' AND t.SJRQ = 0"
    )

    assert reads == {"RM_CALL_MARGIN_PAY_LOG"}
    assert writes == set()


def test_extract_tables_normalizes_oracle_like_placeholder_concatenation():
    reads, writes = extract_tables(
        "select * from WMS_INSTITUTIONAL_INFO where INST_NAME like '%' || 0 || '%'"
    )

    assert reads == {"WMS_INSTITUTIONAL_INFO"}
    assert writes == set()


def test_extract_tables_normalizes_concat_like_placeholder():
    reads, writes = extract_tables(
        "select * from FRMS.RP_WMS_INSTITUTIONAL_INFO where INST_NAME like CONCAT('%', 0, '%')"
    )

    assert reads == {"FRMS.RP_WMS_INSTITUTIONAL_INFO"}
    assert writes == set()


def test_extract_tables_normalizes_in_placeholder_without_parentheses():
    reads, writes = extract_tables(
        "select * from RM_CLIENT_AGREEMENT where CLIENT_UNICODE in 0 ) order by AGREEMENT_ID"
    )

    assert reads == {"RM_CLIENT_AGREEMENT"}
    assert writes == set()


def test_extract_tables_returns_empty_for_unstable_dynamic_mybatis_sql():
    reads, writes = extract_tables(
        "select id from ods.orders where ch_type in ('1', '2', '3') 0\"> and r.id in #{item}"
    )

    assert reads == set()
    assert writes == set()


def test_extract_tables_handles_plain_delete_statements():
    reads, writes = extract_tables("delete from dm.cleanup_target where id = 1")

    assert reads == set()
    assert writes == {"dm.cleanup_target"}


def test_extract_tables_handles_plain_update_statements():
    reads, writes = extract_tables("update dm.cleanup_target set status = 1 where id = 1")

    assert reads == set()
    assert writes == {"dm.cleanup_target"}


def test_extract_tables_excludes_cte_aliases_but_keeps_underlying_tables():
    reads, writes = extract_tables(
        """
        WITH base AS (
            SELECT * FROM ods.orders
        ),
        base1 AS (
            SELECT * FROM dm.dim_user
        ),
        base2 AS (
            SELECT *
            FROM base
            JOIN base1 ON base.user_id = base1.id
        )
        SELECT * FROM base2
        """
    )

    assert reads == {"dm.dim_user", "ods.orders"}
    assert writes == set()


def test_java_parser_emits_method_scoped_statement_facts():
    parser = JavaSqlParser()
    result = parser.parse_file(Path("tests/fixtures/java_method_model/OrderService.java"))

    assert result.methods["syncOrderSummary"].statement_ids == ["sql_0"]
    assert "execute" in result.methods["syncOrderSummary"].calls
    assert "orderRepository.saveSummary" in result.methods["syncOrderSummary"].calls


def test_java_parser_tracks_simple_service_to_repository_calls():
    parser = JavaSqlParser()
    result = parser.parse_file(Path("tests/fixtures/java_method_model/OrderService.java"))

    assert result.methods["syncOrderSummary"].calls == [
        "orderRepository.saveSummary",
        "execute",
    ]


def test_java_parser_extracts_tables_from_mybatis_annotations():
    parser = JavaSqlParser()
    result = parser.parse_file(Path("tests/fixtures/java_annotation_model/AnnotatedMapper.java"))

    assert result.read_tables == ["ods.orders"]
    assert result.write_tables == ["dm.user_order_summary"]
    assert result.methods["loadOrders"].statement_ids == ["sql_0"]
    assert result.methods["saveSummary"].statement_ids == ["sql_1"]


def test_java_parser_extracts_tables_from_value_style_mybatis_annotations():
    parser = JavaSqlParser()
    result = parser.parse_file(Path("tests/fixtures/java_annotation_value_model/ValueAnnotatedMapper.java"))

    assert result.read_tables == ["ods.orders"]
    assert result.write_tables == []
    assert result.methods["loadOrders"].statement_ids == ["sql_0"]


def test_java_parser_extracts_tables_from_concatenated_annotation_sql():
    parser = JavaSqlParser()
    result = parser.parse_file(Path("tests/fixtures/java_annotation_concat_model/ConcatAnnotatedMapper.java"))

    assert result.read_tables == ["ods.orders"]
    assert result.write_tables == ["dm.user_order_summary"]
    assert result.methods["loadOrders"].statement_ids == ["sql_0"]
    assert result.methods["saveSummary"].statement_ids == ["sql_1"]


def test_java_parser_decodes_escaped_newlines_in_annotation_sql():
    parser = JavaSqlParser()
    result = parser.parse_file(Path("tests/fixtures/java_annotation_escaped_model/EscapedAnnotatedMapper.java"))

    assert result.read_tables == ["ods.orders"]
    assert result.write_tables == []
    assert result.methods["loadOrders"].statement_ids == ["sql_0"]


def test_java_parser_extracts_annotated_sql_with_generic_map_return_type_spacing():
    parser = JavaSqlParser()
    result = parser.parse_file(Path("tests/fixtures/java_service_impl_mapper_bridge/AbnRiskMapper.java"))

    assert result.read_tables == ["RP_IB_ABN_RISK_MGMT_DTL_D"]
    assert result.write_tables == []
    assert result.methods["getRiskClsfList"].statement_ids == ["sql_0"]


def test_java_parser_extracts_static_tables_from_xml_mapper():
    parser = JavaSqlParser()
    result = parser.parse_file(Path("tests/fixtures/java_xml_mapper/OrderMapper.java"))

    assert result.read_tables == ["ods.orders"]
    assert result.write_tables == ["dm.user_order_summary"]
    assert result.methods["loadOrders"].statement_ids == ["sql_0"]
    assert result.methods["saveSummary"].statement_ids == ["sql_1"]


def test_java_parser_extracts_tables_from_resources_mapper_layout():
    parser = JavaSqlParser()
    result = parser.parse_file(Path("tests/fixtures/java_mapper_resources/OrderMapper.java"))

    assert result.read_tables == ["ods.orders"]
    assert result.write_tables == []
    assert result.methods["loadOrders"].statement_ids == ["sql_0"]


def test_java_parser_normalizes_where_blocks_and_placeholders_from_xml_mapper():
    parser = JavaSqlParser()
    result = parser.parse_file(Path("tests/fixtures/java_xml_where_mapper/PressureMapper.java"))

    assert result.read_tables == ["RM_PRESSURE_RESULT"]
    assert result.write_tables == []
    assert result.methods["loadByExecId"].statement_ids == ["sql_0"]


def test_java_parser_skips_unstable_dynamic_xml_mapper_sql():
    parser = JavaSqlParser()
    result = parser.parse_file(Path("tests/fixtures/java_dynamic_xml_mapper/DynamicMapper.java"))

    assert result.read_tables == []
    assert result.write_tables == []
    assert result.statements == []
    assert result.methods["findIds"].statement_ids == []


def test_java_symbol_parser_extracts_table_name_annotation():
    source = read_java_source(Path("tests/fixtures/java_mybatis_plus_crud/RpAmFundRiskprofitEntity.java"))

    assert parse_table_name(source) == "RP_AM_FUND_RISKPROFIT"


def test_java_symbol_parser_extracts_basemapper_entity_binding():
    source = read_java_source(Path("tests/fixtures/java_mybatis_plus_crud/RpAmFundRiskprofitMapper.java"))

    assert parse_basemapper_entity(source) == "RpAmFundRiskprofitEntity"


def test_java_parser_exposes_mybatis_plus_static_metadata():
    parser = JavaSqlParser()
    entity_result = parser.parse_file(Path("tests/fixtures/java_mybatis_plus_crud/RpAmFundRiskprofitEntity.java"))
    mapper_result = parser.parse_file(Path("tests/fixtures/java_mybatis_plus_crud/RpAmFundRiskprofitMapper.java"))

    assert entity_result.table_name == "RP_AM_FUND_RISKPROFIT"
    assert entity_result.basemapper_entity is None
    assert mapper_result.table_name is None
    assert mapper_result.basemapper_entity == "RpAmFundRiskprofitEntity"


def test_java_lineage_reducer_derives_crud_reads_and_writes_from_mapper_metadata(tmp_path):
    from bloodline_api.parsers.java_lineage_reducer import reduce_java_modules

    entity_path = tmp_path / "RpAmFundRiskprofitEntity.java"
    entity_path.write_text(
        """
        package com.demo.mybatispluscrud;

        import com.baomidou.mybatisplus.annotation.TableName;

        @TableName("RP_AM_FUND_RISKPROFIT")
        public class RpAmFundRiskprofitEntity {
        }
        """
    )

    mapper_path = tmp_path / "RpAmFundRiskprofitMapper.java"
    mapper_path.write_text(
        """
        package com.demo.mybatispluscrud;

        public interface RpAmFundRiskprofitMapper extends BaseMapper<RpAmFundRiskprofitEntity> {
        }
        """
    )

    service_path = tmp_path / "AnalyticsService.java"
    service_path.write_text(
        """
        package com.demo.mybatispluscrud;

        public class AnalyticsService {
            private RpAmFundRiskprofitMapper rpAmFundRiskprofitMapper;

            public Page<RpAmFundRiskprofitEntity> selectPageResult() {
                return rpAmFundRiskprofitMapper.selectPage(new Page<>(), new LambdaQueryWrapper<>());
            }

            public java.util.List<RpAmFundRiskprofitEntity> selectListResult() {
                return rpAmFundRiskprofitMapper.selectList(new LambdaQueryWrapper<>());
            }

            public RpAmFundRiskprofitEntity selectOneResult() {
                return rpAmFundRiskprofitMapper.selectOne(new LambdaQueryWrapper<>());
            }

            public RpAmFundRiskprofitEntity selectByIdResult() {
                return rpAmFundRiskprofitMapper.selectById(1L);
            }

            public int insertResult() {
                return rpAmFundRiskprofitMapper.insert(new RpAmFundRiskprofitEntity());
            }
        }
        """
    )

    reduced = reduce_java_modules(
        [
            JavaSqlParser().parse_file(entity_path),
            JavaSqlParser().parse_file(mapper_path),
            JavaSqlParser().parse_file(service_path),
        ]
    )

    service = reduced["AnalyticsService"]
    assert service.methods["selectPageResult"].read_tables == ["RP_AM_FUND_RISKPROFIT"]
    assert service.methods["selectListResult"].read_tables == ["RP_AM_FUND_RISKPROFIT"]
    assert service.methods["selectOneResult"].read_tables == ["RP_AM_FUND_RISKPROFIT"]
    assert service.methods["selectByIdResult"].read_tables == ["RP_AM_FUND_RISKPROFIT"]
    assert service.methods["insertResult"].write_tables == ["RP_AM_FUND_RISKPROFIT"]


def test_java_lineage_reducer_does_not_treat_serviceimpl_with_extra_calls_as_pure_wrapper(tmp_path):
    from bloodline_api.parsers.java_lineage_reducer import reduce_java_modules

    entity_path = tmp_path / "ReportEntity.java"
    entity_path.write_text(
        """
        package com.demo.mybatispluscrud;

        import com.baomidou.mybatisplus.annotation.TableName;

        @TableName("REPORT_TABLE")
        public class ReportEntity {
        }
        """
    )

    mapper_path = tmp_path / "ReportMapper.java"
    mapper_path.write_text(
        """
        package com.demo.mybatispluscrud;

        public interface ReportMapper extends BaseMapper<ReportEntity> {
            @org.apache.ibatis.annotations.Select("select * from REPORT_TABLE")
            java.util.List<ReportEntity> getRiskClsfList();
        }
        """
    )

    service_path = tmp_path / "ReportServiceImpl.java"
    service_path.write_text(
        """
        package com.demo.mybatispluscrud;

        public class ReportServiceImpl extends ServiceImpl<ReportMapper, ReportEntity> {
            public java.util.List<ReportEntity> getRiskClsfList() {
                audit();
                getBaseMapper();
                return null;
            }

            public Page<ReportEntity> outer() {
                return getRiskClsfList();
            }

            private void audit() {
            }
        }
        """
    )

    reduced = reduce_java_modules(
        [
            JavaSqlParser().parse_file(entity_path),
            JavaSqlParser().parse_file(mapper_path),
            JavaSqlParser().parse_file(service_path),
        ]
    )

    service = reduced["ReportServiceImpl"]
    assert service.methods["getRiskClsfList"].read_tables == []
    assert service.methods["outer"].read_tables == []


def test_java_lineage_reducer_does_not_resolve_ambiguous_interface_impls_by_convention(tmp_path):
    from bloodline_api.parsers.java_lineage_reducer import reduce_java_modules

    entity_path = tmp_path / "ReportEntity.java"
    entity_path.write_text(
        """
        package com.demo.mybatispluscrud;

        import com.baomidou.mybatisplus.annotation.TableName;

        @TableName("REPORT_TABLE")
        public class ReportEntity {
        }
        """
    )

    mapper_path = tmp_path / "ReportMapper.java"
    mapper_path.write_text(
        """
        package com.demo.mybatispluscrud;

        public interface ReportMapper extends BaseMapper<ReportEntity> {
            @org.apache.ibatis.annotations.Select("select * from REPORT_TABLE")
            java.util.List<ReportEntity> getRiskClsfList();
        }
        """
    )

    primary_impl_path = tmp_path / "ReportServiceImpl.java"
    primary_impl_path.write_text(
        """
        package com.demo.mybatispluscrud;

        public class ReportServiceImpl extends ServiceImpl<ReportMapper, ReportEntity> implements IReportService {
            public java.util.List<ReportEntity> getRiskClsfList() {
                return getBaseMapper().getRiskClsfList();
            }
        }
        """
    )

    secondary_impl_path = tmp_path / "AltReportServiceImpl.java"
    secondary_impl_path.write_text(
        """
        package com.demo.mybatispluscrud;

        public class AltReportServiceImpl implements IReportService {
        }
        """
    )

    interface_path = tmp_path / "IReportService.java"
    interface_path.write_text(
        """
        package com.demo.mybatispluscrud;

        public interface IReportService {
        }
        """
    )

    controller_path = tmp_path / "ReportApi.java"
    controller_path.write_text(
        """
        package com.demo.mybatispluscrud;

        public class ReportApi {
            private IReportService reportService;

            public java.util.List<ReportEntity> load() {
                return reportService.getRiskClsfList();
            }
        }
        """
    )

    reduced = reduce_java_modules(
        [
            JavaSqlParser().parse_file(entity_path),
            JavaSqlParser().parse_file(mapper_path),
            JavaSqlParser().parse_file(primary_impl_path),
            JavaSqlParser().parse_file(secondary_impl_path),
            JavaSqlParser().parse_file(interface_path),
            JavaSqlParser().parse_file(controller_path),
        ]
    )

    controller = reduced["ReportApi"]
    assert controller.methods["load"].read_tables == []


def test_java_symbol_parser_ignores_locals_in_package_private_methods_and_constructors():
    source = """
    package com.demo;

    public class DemoService {
        DemoService() {
            String constructorLocal = "x";
        }

        void packagePrivateMethod() {
            Integer methodLocal = 1;
        }

        private String actualField;
    }
    """

    assert parse_field_types(source) == {"actualField": "String"}


def test_java_symbol_parser_extracts_metadata_from_primary_declaration_only():
    entity_source = """
    package com.demo;

    // @TableName("WRONG_COMMENT")
    /* @TableName("WRONG_BLOCK") */
    @TableName("RIGHT_TABLE")
    public class DemoEntity {
        @TableName("INNER_TABLE")
        private String ignoredField;
    }
    """

    mapper_source = """
    package com.demo;

    public interface DemoMapper /* extends BaseMapper<WrongEntity> */ extends BaseMapper<RealEntity> {
    }
    """

    assert parse_table_name(entity_source) == "RIGHT_TABLE"
    assert parse_basemapper_entity(mapper_source) == "RealEntity"


def test_java_symbol_parser_extracts_controller_field_types():
    source = read_java_source(Path("tests/fixtures/java_api_interface_controller/ReportController.java"))

    assert parse_field_types(source) == {"reportService": "IReportService"}


def test_java_symbol_parser_preserves_generic_controller_field_types():
    source = read_java_source(
        Path("tests/fixtures/java_api_generic_interface_controller/GenericReportController.java")
    )

    assert parse_field_types(source) == {"reportService": "IReportService<ReportRow>"}


def test_java_symbol_parser_extracts_implemented_generic_interfaces():
    source = read_java_source(
        Path("tests/fixtures/java_api_generic_interface_controller/ReportServiceImpl.java")
    )

    assert parse_implemented_types(source) == ["IReportService"]


def test_java_lineage_reducer_strips_generic_qualifiers_from_declared_types():
    from bloodline_api.parsers.java_lineage_reducer import _candidate_module_names_from_type

    assert _candidate_module_names_from_type("com.demo.IReportService<com.demo.ReportRow>") == [
        "ReportServiceImpl",
        "ReportService",
        "IReportServiceImpl",
        "IReportService",
    ]


def test_java_symbol_parser_extracts_normalized_implemented_types():
    from bloodline_api.parsers.java_symbol_parser import parse_implemented_types

    source = read_java_source(
        Path("tests/fixtures/java_api_unique_impl_binding/DailyReportAdapter.java")
    )

    assert parse_implemented_types(source) == ["IReportService"]


def test_java_symbol_parser_extracts_serviceimpl_superclass():
    from bloodline_api.parsers.java_symbol_parser import parse_extended_type

    source = read_java_source(Path("tests/fixtures/java_service_impl_bridge/UserServiceImpl.java"))

    assert parse_extended_type(source) == "ServiceImpl<UserMapper, UserEntity>"


def test_java_controller_parser_extracts_http_endpoint_facts():
    endpoints = parse_controller_endpoints(
        Path("tests/fixtures/java_api_controller/OrderSummaryController.java")
    )

    assert [(item.http_method, item.route, item.method_name) for item in endpoints] == [
        ("GET", "/api/orders/{id}", "getSummary"),
        ("POST", "/api/orders/summary", "refreshSummary"),
    ]
    assert [item.endpoint_key for item in endpoints] == [
        "api:GET /api/orders/{id}",
        "api:POST /api/orders/summary",
    ]


def test_java_controller_parser_handles_generic_return_types():
    endpoints = parse_controller_endpoints(
        Path("tests/fixtures/java_api_interface_controller/AssetManagementNetWorthController.java")
    )

    assert [(item.http_method, item.route, item.method_name) for item in endpoints] == [
        ("GET", "/assetManagement/selectAssetManagementNetWorth", "selectAssetManagementNetWorth"),
        ("GET", "/assetManagement/calculate", "calculate"),
    ]
