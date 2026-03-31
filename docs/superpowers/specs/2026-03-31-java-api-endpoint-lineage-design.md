# Java API Endpoint 血缘设计

## 1. 背景

当前 BloodLine Analysis 在 Java 侧已经具备：

- 静态 SQL 字符串抽取
- 最小方法级事实模型
- 最小方法调用图
- 方法级事实归并回模块级表读写关系
- MyBatis 注解 SQL 与同 stem XML Mapper 的最小静态支持

现阶段 Java 侧的“终点”仍然主要落在表节点：

- `java_module -> READS/WRITES -> table`
- `table -> FLOWS_TO -> table`

这意味着图谱更偏“数据落到哪里”，而缺少“哪些对外 HTTP 接口最终会读取或写入这些表”的表达。对排查消费链路、面向 API 视角理解血缘时，这一层是缺失的。

因此本轮目标是在现有 Java 解析基础上，新增一种面向消费端的最终节点：

- `api_endpoint`

用于承接 Spring MVC Controller 层暴露的 HTTP 路由。

## 2. 目标

本轮设计目标是：

1. 识别 Spring MVC 风格的 HTTP 接口节点
2. 使用“路由形式”命名接口节点，例如：
   - `GET /api/orders/{id}`
   - `POST /api/orders/summary`
3. 沿现有方法调用链，把接口方法最终触达的表读写事实归并到 API 层
4. 在图中把 `api_endpoint` 作为新的最终节点类型展示
5. 在对象详情页与相关查询结果中体现“哪些 API 会触达当前表”

## 3. 非目标

本轮不包含：

- Feign / RPC / Dubbo 等非 HTTP 接口
- 非 Spring MVC 风格框架
- 请求参数与响应 DTO 的字段级映射
- 字段级血缘
- OpenAPI 生成、接口文档自动同步
- Controller 外的通用 Web 框架适配

## 4. 用户可见结果

落地后，用户应能看到：

1. 某些 Java 侧终点不再只停在最终落表，还能继续穿透到 HTTP API 层
2. 与某张表相关的详情页中，可以看到触达该表的 API 节点
3. 链路图中，API 节点会作为一类新的终点类型出现
4. API 节点命名使用 HTTP 方法 + 完整路由，而不是 Java 方法名

## 5. 总体方案

采用“在现有 Java 方法事实与调用图之上，新增 API 入口层”的方案。

整体链路：

1. 解析 Java Controller 类与路由注解
2. 识别 Controller 方法对应的完整 HTTP 路由
3. 把路由方法映射到现有方法级事实模型
4. 沿已有方法调用图继续归并读写表
5. 生成新的 `api_endpoint` 节点和相关事实

这样可以复用已经完成的：

- 方法级事实模型
- 方法调用图
- 表级归并逻辑

而不需要另起一套完全独立的解析器。

## 6. 节点与图模型设计

### 6.1 新增节点类型

新增图节点类型：

- `api_endpoint`

节点 key 形式：

- `api:GET /api/orders/{id}`
- `api:POST /api/orders/summary`

节点 `name` 与 key 的可读部分一致，优先直接使用：

- `GET /api/orders/{id}`

### 6.2 与现有节点关系

第一版建议使用两层关系：

1. 事实层
   - `api_endpoint READS table`
   - `api_endpoint WRITES table`

2. 展示层
   - 当前前端链路图可直接把 `api_endpoint` 作为一类终点节点渲染
   - 暂不额外派生 `FLOWS_TO` 到 API 节点

也就是说，表之间的 `FLOWS_TO` 继续只用于表级传播；API 节点通过 `READS/WRITES` 与表连接。

这样做的原因：

- 保持当前 `FLOWS_TO` 语义稳定
- 避免把“数据传播边”和“消费入口边”混为一类
- 便于后续分别控制前端展示

## 7. Java 解析设计

### 7.1 解析目标

第一版只解析 Spring MVC 常见路由注解：

- 类级：
  - `@RequestMapping`
- 方法级：
  - `@GetMapping`
  - `@PostMapping`
  - `@PutMapping`
  - `@DeleteMapping`
  - `@PatchMapping`
  - `@RequestMapping`

### 7.2 路由命名规则

完整路由由两部分拼接：

1. 类级 base path
2. 方法级 path

并结合 HTTP method 生成最终显示值：

- `GET /api/orders/{id}`

归一化规则：

- 统一保留前导 `/`
- 重复斜杠折叠
- method 统一大写
- path 使用源码中的字面值，不做参数推导

### 7.3 方法映射规则

每个识别到的 API 路由，都要绑定到一个明确的 Java 方法：

- `ControllerClass#methodName`

然后沿现有方法调用图做递归归并，得到该 API 方法最终触达的表集合。

### 7.4 保守策略

以下场景第一版保守跳过或降级：

- 动态拼接 path
- 多层复杂继承带来的路由合成
- 条件路由 / 多 method 数组的复杂组合
- 反射调用

原则是：

- 宁可少识别
- 不要误造错误 API 节点

## 8. 中间事实模型设计

在现有 `JavaMethodFact` 基础上，新增一层 API 事实模型。

建议新增：

- `JavaApiEndpointFact`

字段建议：

- `endpoint_key`
- `route`
- `http_method`
- `controller_module_name`
- `method_name`
- `read_tables`
- `write_tables`

其中 `read_tables / write_tables` 不在初始解析阶段直接写死，而是通过现有 reducer 沿调用图归并得到。

## 9. 后端实现拆分

### 9.1 解析层

建议新增一个解析器，例如：

- `java_controller_parser.py`

职责：

- 识别 Controller 类
- 提取类级 / 方法级路由注解
- 生成 `JavaApiEndpointFact`

### 9.2 归并层

建议在当前 `java_lineage_reducer.py` 附近补一层 API 归并逻辑，例如：

- `reduce_java_api_endpoints(...)`

职责：

- 根据 API 方法入口
- 调用现有方法级 reducer
- 得到 API 节点最终读写的表集合

### 9.3 持久化层

扫描流程里：

1. 先建 `java_module`
2. 再建 `api_endpoint`
3. 为 `api_endpoint` 写入：
   - `READS`
   - `WRITES`
   到表节点

并允许详情页通过已有 related-object 聚合逻辑读取它们。

## 10. 前端展示设计

### 10.1 对象详情页

在 `related_objects` 中新增：

- `api_endpoints`

展示方式与：

- `jobs`
- `java_modules`
- `transformations`

保持同一风格。

### 10.2 链路图

链路图增加一种新节点类型：

- `api_endpoint`

视觉上建议作为“终点节点”展示，但仍保留可点击与跳转能力。

### 10.3 搜索

第一版不要求首页主搜索立即把 API 节点与表混在一起；可以先只在详情关联对象和链路图中展示。

如果后续确认需要，再扩展全局搜索入口。

## 11. 测试设计

至少补以下测试：

1. 解析测试
   - Controller 类级 / 方法级注解解析
   - 路由拼接正确
   - HTTP method 提取正确

2. 归并测试
   - `Controller -> Service -> Repository` 可归并到表
   - API 节点能拿到最终读写表集合

3. 持久化测试
   - 扫描后可创建 `api_endpoint` 节点
   - `api_endpoint READS/WRITES table` 正确落库

4. API 回归测试
   - 表详情页 `related_objects` 包含 `api_endpoints`

5. 前端测试
   - 详情页可展示 API 关联对象
   - 链路图可渲染 API 节点

## 12. 风险与权衡

### 风险 1：Spring 注解语法覆盖不足

不同项目的 Controller 写法差异很大。第一版如果追求覆盖太广，容易误识别。

应对：

- 只支持最常见、最稳定的注解路径
- 其他情况保守跳过

### 风险 2：API 路由与方法调用链映射不稳定

如果路由识别出来了，但方法调用链不完整，就会出现 API 节点存在但不连表。

应对：

- 允许 API 节点存在但无表关系
- 先保证正确，不强行补全

### 风险 3：图复杂度上升

加入 API 节点后，详情页图会更复杂。

应对：

- 第一版只在详情页链路与关联对象里展示
- 不强制进入首页全局图

## 13. 实施边界总结

第一版范围固定为：

- 只做 HTTP 接口
- 只做 Spring MVC Controller
- 节点命名为 `METHOD + route`
- 基于现有方法调用图归并到表
- 在详情页与链路图里展示 API 节点

不做：

- RPC / Feign / Dubbo
- 字段级接口映射
- 动态 route 完整展开
- 全局搜索一开始就混入 API 节点

## 14. 推荐实施顺序

1. 先定义 `JavaApiEndpointFact`
2. 增加 Controller / Route 解析器
3. 增加 API -> 方法 -> 表 的 reducer
4. 接入扫描持久化
5. 扩展详情页 `related_objects`
6. 扩展链路图 API 节点展示
7. 最后补文档与回归测试
