# 视图定义血缘解析设计

日期：2026-04-01  
关联 Issue：`#39`

## 1. 背景

当前项目已经完成 MySQL 元数据接入，能够：

- 从 `information_schema.tables` / `information_schema.columns` 读取表和视图元数据
- 为 `data_table` / `table_view` 节点补充元数据
- 在页面中展示字段数、中文名称等摘要信息

但当前 `table_view` 仍然只停留在“对象识别”层，没有利用 `INFORMATION_SCHEMA.VIEWS.VIEW_DEFINITION` 继续解析其底层依赖，因此：

- 视图不会向底层表或视图建立血缘边
- 视图节点无法完整进入详情页完整链路图
- 解析失败时，页面也无法解释为什么该视图没有展开出底层依赖

本设计的目标是把 `VIEW_DEFINITION` 纳入血缘解析主线，同时保持扫描稳定性。

## 2. 目标

本轮目标：

1. 从 `INFORMATION_SCHEMA.VIEWS` 读取 `VIEW_DEFINITION`
2. 对 `table_view` 节点解析底层依赖对象
3. 将视图血缘接入现有表级血缘图与详情页完整链路图
4. 对解析失败的视图保存失败状态与错误信息
5. 在视图详情页显式展示失败信息，帮助排障

## 3. 非目标

本轮不做：

- 字段级视图血缘
- 复杂方言的完整兼容
- 视图定义的 SQL 美化或编辑
- 因单个视图解析失败而中断整次扫描
- 数据库以外的视图定义来源

## 4. 方案概览

本轮采用“分层严格”方案：

- 视图定义解析成功：
  - 产出 `underlying object -> table_view` 血缘
  - 让视图继续进入现有表级派生与详情页链路图
- 视图定义解析失败：
  - 不阻断整次扫描
  - 保存 `view_definition`、解析状态、错误信息
  - 详情页展示“解析失败”及具体原因

也就是说，本轮默认优先保障扫描可用性，但不会静默吞掉失败信息。

## 5. 数据读取设计

### 5.1 读取范围

在现有 `MySQLMetadataLoader` 基础上，新增从 `information_schema.views` 读取：

- `table_schema`
- `table_name`
- `view_definition`

读取范围仍受：

- `mysql_dsn`
- `metadata_databases`

控制，保持与现有 metadata 白名单一致。

### 5.2 中间结构扩展

扩展 `MySQLMetadataObject`，新增字段：

- `view_definition: str | None`

规则：

- 普通表：`view_definition = None`
- 视图：写入 `INFORMATION_SCHEMA.VIEWS.VIEW_DEFINITION`

## 6. 存储设计

### 6.1 object_metadata 扩展

在现有 `object_metadata` 表上增加字段：

- `view_definition`
- `view_parse_status`
- `view_parse_error`

建议取值：

- `view_parse_status`
  - `not_applicable`
  - `parsed`
  - `failed`

说明：

- `data_table` 节点固定写 `not_applicable`
- `table_view` 节点根据解析结果写 `parsed` 或 `failed`

### 6.2 object_metadata_columns

字段表不需要结构变化，本轮继续只保存字段元信息。

## 7. 解析与血缘生成

### 7.1 解析入口

在 MySQL metadata 接入扫描流程时，对 `object_kind=view` 的对象执行额外步骤：

1. 读取 `view_definition`
2. 调用现有 SQL 表对象抽取逻辑
3. 解析出视图底层依赖对象集合

第一版优先复用现有 SQL 抽取器，避免单独维护另一套视图 SQL 解析器。

### 7.2 产出边

对每个解析成功的视图：

- 为底层对象建立到视图的依赖边
- 方向为：
  - `underlying table/view -> current view`

然后继续让视图参与现有 `FLOWS_TO` 派生逻辑，使其自然出现在：

- 搜索
- 详情页
- 完整链路图
- 闭环分析（如形成环）

### 7.3 解析失败

如果 `view_definition` 解析失败：

- 不抛出扫描级异常
- 不建立该视图的底层依赖边
- 保存：
  - `view_definition`
  - `view_parse_status = failed`
  - `view_parse_error = 具体异常`

## 8. 页面展示设计

### 8.1 详情页

若当前对象为 `table_view`：

- 正常显示元数据摘要
- 额外显示“视图解析状态”

当状态为：

- `parsed`
  - 展示“已解析”
- `failed`
  - 展示“解析失败”
  - 展示具体失败信息

可选补充：

- 视图定义摘要或折叠块

但第一版至少保证失败原因可见。

### 8.2 完整链路图

解析成功的 `table_view` 会像普通对象一样进入完整链路图。  
解析失败的视图仍作为节点存在，但由于缺失底层依赖边，其链路信息会不完整。

## 9. 错误处理

### 9.1 连接级错误

仍沿用现有 MySQL metadata 连接错误处理逻辑：

- DSN 配置错误
- 主机名无法解析
- 权限不足

这类错误属于 metadata load 阶段错误。

### 9.2 视图解析错误

视图解析错误不升级成整次扫描失败，而是：

- 降级为对象级失败状态
- 进入 `object_metadata.view_parse_error`
- 在详情页给用户可见反馈

## 10. 测试策略

需要覆盖：

1. `INFORMATION_SCHEMA.VIEWS` 读取成功
2. 视图定义成功解析并建立血缘边
3. 视图定义解析失败但扫描整体成功
4. 失败状态与错误信息正确写入 `object_metadata`
5. 详情页能返回并展示失败信息

建议新增两类 fixture：

- 可稳定解析的静态视图定义
- 故意失败的复杂/非法视图定义

## 11. 风险与权衡

### 风险 1：数据库方言差异

`VIEW_DEFINITION` 可能包含：

- 方言函数
- 特殊引号
- 数据库特定语法

应对：

- 第一版默认允许对象级失败
- 保留失败信息，后续按真实样本补解析能力

### 风险 2：视图嵌套视图

如果视图依赖另一个视图，理论上也应被识别为底层对象。

第一版策略：

- 只要 SQL 抽取器能识别到对象名，就正常建立 `view -> view` 或 `table -> view` 关系
- 不做多层递归展开增强

### 风险 3：长 SQL 展示过载

完整 `view_definition` 可能很长。

第一版策略：

- 数据库存储完整定义
- 前端只展示失败信息
- 如需展示定义内容，优先折叠或摘要

## 12. 实施拆分建议

建议拆成 5 个任务：

1. 扩展 MySQL metadata connector 读取 `VIEW_DEFINITION`
2. 扩展 `object_metadata` 落库字段
3. 视图定义解析并建立视图血缘
4. 详情页展示视图解析状态与失败信息
5. 增加回归测试并更新文档

