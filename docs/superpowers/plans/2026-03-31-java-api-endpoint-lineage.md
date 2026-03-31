# Java API Endpoint 血缘实施计划

## 1. 目标

在现有 Java 方法级事实、最小调用图与表级归并的基础上，新增 HTTP API 路由节点：

- 识别 Spring MVC 风格 Controller 路由
- 生成 `api_endpoint` 节点
- 让接口节点继承其调用链最终触达的表读写事实
- 在对象详情页与链路图中展示 API 终点

本轮保持保守范围：

- 仅支持 HTTP 接口
- 仅支持 Spring MVC 常见映射注解
- 不做字段级映射
- 不引入 RPC / Feign / OpenAPI 同步

## 2. 实施分解

### 阶段 A：补 API 入口事实

1. 新增 `java_controller_parser.py`
2. 识别：
   - `@RequestMapping`
   - `@GetMapping`
   - `@PostMapping`
   - `@PutMapping`
   - `@DeleteMapping`
   - `@PatchMapping`
3. 组合类级和方法级路径，归一化得到：
   - `GET /api/orders/{id}`
4. 新增 `JavaApiEndpointFact`
5. 将 endpoint 事实与现有方法事实建立绑定关系：
   - `controller_module_name`
   - `method_name`
   - `endpoint_key`

### 阶段 B：将 API 入口归并到表读写事实

1. 在 `java_lineage_reducer.py` 旁新增 API reducer
2. 给每个 API 入口沿现有方法调用图归并：
   - `read_tables`
   - `write_tables`
3. 保持保守策略：
   - 无法稳定识别的路由不入图
   - 无法稳定关联的方法不归并

### 阶段 C：持久化与查询接入

1. 扫描流程写入 `api_endpoint` 节点
2. 持久化：
   - `api_endpoint READS table`
   - `api_endpoint WRITES table`
3. 扩展 `related_objects`
   - 新增 `api_endpoints`
4. 确保详情页专用 `connected-lineage` 接口能把 API 节点带出来
5. 第一版不派生 `FLOWS_TO` 到 API 节点

### 阶段 D：前端展示

1. 扩展前端类型定义
2. 在详情页“关联对象”区域新增 API 分组
3. 在链路图中把 `api_endpoint` 作为新节点类型渲染
4. 视觉上把 API 节点处理为消费端终点
5. 保持现有局部子图模式，不恢复全量请求

### 阶段 E：测试与文档

1. 新增后端 fixture：
   - Controller
   - Service
   - Repository
2. 覆盖：
   - 路由抽取
   - 方法绑定
   - API -> 表 归并
   - 详情页 related objects 返回 API
3. 前端测试：
   - 详情页 API 关联对象显示
   - 链路图 API 节点渲染
4. 更新：
   - `README.md`
   - 设计文档
   - UAT 手册

## 3. 预计改动文件

后端核心：

- `backend/src/bloodline_api/parsers/java_controller_parser.py`
- `backend/src/bloodline_api/parsers/java_lineage_reducer.py`
- `backend/src/bloodline_api/parsers/java_sql_parser.py`
- `backend/src/bloodline_api/services/lineage_query.py`
- `backend/src/bloodline_api/schemas.py`

前端核心：

- `frontend/src/types.ts`
- `frontend/src/pages/TableDetailPage.tsx`
- `frontend/src/components/ConnectedLineageGraph.tsx`
- `frontend/src/graph/overviewGraph.ts`
- `frontend/src/components/RelatedObjectsPanel.tsx`

测试与 fixture：

- `backend/tests/test_java_sql_parser.py`
- `backend/tests/test_tables_api.py`
- `frontend/src/__tests__/TableDetailChainGraph.test.tsx`
- `backend/tests/fixtures/java_*`

## 4. 执行顺序

建议按这个顺序实施：

1. 先补 Controller 路由事实模型与解析
2. 再补 API reducer
3. 再接扫描持久化与查询
4. 再改前端详情页和链路图
5. 最后统一补文档与回归测试

## 5. 风险与控制

### 风险 1：路由误识别

控制：

- 只支持常见 Spring 注解
- 仅处理字面量 path
- 复杂动态 path 保守跳过

### 风险 2：Controller 方法无法稳定归并到调用链

控制：

- 先复用现有方法调用图
- 只在存在稳定方法事实时建立 API 入口

### 风险 3：前端图复杂度继续上升

控制：

- 仅在详情页局部子图里展示 API 节点
- 不恢复全局图
- 不把 API 节点纳入第一版全局搜索

## 6. 完成标准

满足以下条件即可认为本轮完成：

1. 详情页可看到与当前表相关的 API 节点
2. 链路图中 API 节点可作为终点显示
3. API 节点使用路由形式命名
4. 后端测试、前端测试、构建全部通过
5. 文档同步完成
