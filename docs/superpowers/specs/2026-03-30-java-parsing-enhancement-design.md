# Java 代码解析增强设计

日期：2026-03-30  
关联 Epic：[#10 Java 代码解析增强](https://github.com/yzh1990223/BloodLine-Analysis/issues/10)

## 1. 目标

在当前 Java 字符串 SQL 解析能力基础上，补齐一批更贴近真实工程的 Java 代码解析能力，重点提升：

- Spring 风格 `DAO / Repository / Service` 调用链上的表级血缘覆盖率
- Java 解析结果与现有对象归并逻辑的一致性
- 对一部分 MyBatis 风格场景的稳定识别能力

本轮目标是提升对象级 / 表级血缘正确性，不进入字段级血缘。

## 2. 当前现状

当前后端 Java 解析入口在：

- `/Users/nathan/Documents/GithubProjects/BloodLine Analysis/backend/src/bloodline_api/parsers/java_sql_parser.py`

其核心能力是：

- 扫描 Java 文件中的字符串字面量
- 只保留看起来像 SQL 起始语句的字符串
- 使用 `sql_table_extractor.py` 提取 `read_tables` / `write_tables`
- 产出模块级与语句级事实

当前明显边界：

- 只能识别“直接出现在字符串字面量中的 SQL”
- 不能表达方法调用关系
- 不能沿 `Service -> Repository -> DAO` 调用链归并 SQL 事实
- 对 MyBatis 风格尚未建模
- 对封装方法、常量拼接、注解 SQL 的覆盖率较低

因此当前 Java 解析仍属于 MVP 级别的“直接 SQL 抽取器”，尚不是“Java 工程解析器”。

## 3. 设计目标

本轮设计采用三层解析方案：

1. 字符串 SQL 抽取层
2. 方法调用图层
3. 表级归并层

这样可以在不把现有解析器推倒重来的情况下，逐步提升 Java 工程风格下的表级血缘效果。

### 3.1 主目标

- 支持 Java 文件中的直接 SQL 字符串识别
- 支持 Spring 风格 `Service / Repository / DAO` 之间的方法调用归并
- 支持一部分容易稳定识别的 MyBatis 风格场景
- 让最终结果仍然落回现有对象级 / 表级图模型

### 3.2 本轮不做

- 字段级血缘
- 复杂动态 SQL 的完整还原
- 全框架通用静态分析
- Java AST 的完整语义解析器
- MyBatis XML 的全语法覆盖

## 4. 适用范围与优先级

### 4.1 优先支持

1. Java 文件里的字符串 SQL
2. Spring 风格 `DAO / Repository / Service` 调用链
3. MyBatis 注解 SQL

### 4.2 兼容支持

- 命名较稳定、映射关系简单的 MyBatis XML Mapper

### 4.3 暂不支持

- 大量依赖运行时拼接的 SQL
- 复杂条件片段、模板片段组合
- 框架魔法生成 SQL

## 5. 方案选择

### 方案 A：分层解析

分成三层：

- 第 1 层：增强字符串 SQL 抽取
- 第 2 层：建立方法级调用关系
- 第 3 层：把“方法 -> SQL / 对象”的关系归并回表级血缘

优点：

- 与现有实现兼容
- 模块边界清楚
- 便于后续继续扩 Spring / MyBatis
- 后续也容易为字段级能力预留接口

缺点：

- 比单纯正则抽取更复杂
- 需要引入“方法级中间事实”

### 方案 B：继续在现有解析器里打补丁

优点：

- 开发快

缺点：

- 规则会迅速堆叠
- 难以维护
- 不利于后续框架扩展

### 方案 C：框架特化优先

优点：

- 对 Spring / MyBatis 某些场景见效快

缺点：

- 很容易演变成框架特例集合
- 复用性差

### 结论

采用方案 A：分层解析。

## 6. 模块设计

建议新增或重构为以下结构：

- `java_sql_parser.py`
  - 继续负责字符串 SQL 抽取
- `java_symbol_parser.py`
  - 负责类、方法、注解、简化调用关系识别
- `java_call_graph.py`
  - 负责生成方法级调用图
- `java_mapper_parser.py`
  - 负责 MyBatis 注解 SQL 与最小 XML Mapper 支持
- `java_lineage_reducer.py`
  - 负责将方法级事实归并为模块级 / 表级事实

第一版不要求文件一定完全拆到上述粒度，但逻辑职责应按这个边界组织。

## 7. 三层解析模型

### 7.1 第一层：字符串 SQL 抽取层

继续保留当前优势，但增强识别来源：

- 直接字符串字面量 SQL
- 常量变量承载的 SQL
- 注解中的 SQL 文本

这一层输出：

- `JavaSqlStatement`
- 每条语句的 `read_tables`
- 每条语句的 `write_tables`
- 语句归属的方法信息

### 7.2 第二层：方法调用图层

第一版不追求完整 Java AST，只做“足够稳定”的方法级关系：

- 当前类内方法调用
- 同文件内 `service -> repository -> dao` 调用
- 简单 Bean 成员调用
- 简单 `this.xxx()` / `field.xxx()` 模式

目标不是得到完整调用图，而是让“某个上层业务方法最终触达哪些 SQL / 表”能被归并。

这一层输出：

- 方法节点
- 方法调用边
- 方法到 SQL 事实的关联

### 7.3 第三层：表级归并层

把方法级事实归并成当前图模型可消费的结果：

- Java 模块触达的表
- 每条独立 SQL 语句触达的表
- 通过方法调用链归并出的读写表集合

这一层要特别避免“同模块内所有 SQL 被粗暴合并成直接下游”的老问题。

## 8. 支持的 Java / Spring 场景

第一版优先支持：

- `Service -> Repository -> DAO`
- `Repository -> JdbcTemplate`
- `DAO -> String SQL`
- `prepareStatement(...)`
- `jdbcTemplate.query/update(...)`
- 命名清晰的方法包装

要求：

- 结果至少能把最终读写表归并到调用链上
- 不要求展示完整方法图 UI

## 9. 支持的 MyBatis 场景

### 9.1 本轮支持

- 注解 SQL：
  - `@Select`
  - `@Insert`
  - `@Update`
  - `@Delete`
- 命名稳定、可直接定位的 XML Mapper 最小支持：
  - `namespace`
  - `id`
  - 语句体中静态 SQL

### 9.2 本轮不支持

- 大量动态标签组合后的精确 SQL 还原
- 复杂 include / fragment / choose / foreach 全量展开

对 XML Mapper 的策略应偏保守：宁可少识别，不误识别。

## 10. 中间数据结构

建议新增方法级中间结构，例如：

- `JavaMethodFact`
  - `class_name`
  - `method_name`
  - `calls`
  - `sql_statement_ids`
- `JavaModuleFact`
  - `module_name`
  - `methods`
  - `read_tables`
  - `write_tables`

它们是解析中间层，不一定都要持久化到 SQLite。

第一版建议：

- 中间结构只在内存中用于归并
- 持久化仍然只保留当前图模型真正需要的模块 / 表级事实

## 11. 与现有图模型的关系

当前系统已有：

- `java_module`
- `READS`
- `WRITES`
- 由图服务派生的 `FLOWS_TO`

Java 解析增强后，仍然遵守这个图模型：

- Java 方法级关系只作为解析内部事实
- 对外仍然沉淀为：
  - `java_module -> table` 的 `READS / WRITES`
  - 必要时保留独立语句级事实用于避免误归并

重点是提升“结果正确性”，而不是扩图模型复杂度。

## 12. 与对象归并的关系

本轮目标之一是提升对象归并准确性，因此 Java 解析增强需要配合：

- 统一表名归一化
- 与 `.repo` 解析结果统一 key 规则
- 避免因为模块级过度聚合而生成错误 `FLOWS_TO`

具体要求：

- 保留语句级事实边界
- 通过方法归并时，只沿真实调用关系传播
- 不允许简单把一个类内所有 SQL 全部连成直接上下游

## 13. 风险与约束

### 13.1 主要风险

- 方法调用静态分析不完整，导致漏链
- 误把同名方法或同名 Bean 调用连错
- MyBatis XML 解析过深导致误判
- 规则扩展过快，解析器变成特例集合

### 13.2 控制策略

- 第一版只支持稳定模式
- 对不确定调用关系宁可不归并
- XML Mapper 只做最小可稳定支持
- 保持语句级事实边界

## 14. 测试策略

测试至少覆盖：

1. 直接 SQL 字符串
2. 类内方法封装
3. `Service -> Repository -> DAO` 调用链
4. `JdbcTemplate` 风格
5. 注解 SQL
6. 最小 XML Mapper
7. 不能稳定识别时的保守退化
8. 不应出现的错误直连回归

建议增加新的 fixture 目录，例如：

- `tests/fixtures/java/spring_repo/`
- `tests/fixtures/java/mybatis_mapper/`

## 15. 拟拆分子任务

建议拆成第一批任务：

1. 明确 Java 方法级中间事实模型
2. 增强字符串 SQL / 注解 SQL 抽取
3. 建立简化方法调用图
4. 增加 Spring 风格调用链归并
5. 增加 MyBatis 最小支持
6. 调整表级归并逻辑避免错误直连
7. 补充 fixture、回归测试与文档

## 16. 验收标准

本轮完成后应满足：

- Spring 风格 `Service / Repository / DAO` 场景的表级覆盖率明显提升
- 一部分 MyBatis 风格场景可稳定识别
- Java 结果与现有对象归并逻辑更一致
- 不再因为同模块 SQL 粗暴合并产生明显错误直连
- README / 设计文档 / UAT 文档同步更新

## 17. 后续演进

本轮完成后，后续可以继续演进：

- 更完整的 XML Mapper 支持
- 更强的 Bean / 注入关系识别
- 与 MySQL 元数据接入联动提升归一化能力
- 为字段级血缘提供更稳的前置基础
