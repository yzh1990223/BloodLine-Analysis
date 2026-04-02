# MyBatis-Plus CRUD Lineage Design

## 1. Background

`#41 Java API 血缘增强` 当前已经支持：

- Spring MVC Controller 路由识别
- `Controller -> Service -> Mapper/XML/注解 SQL` 的部分穿透
- `ServiceImpl.getBaseMapper().自定义方法()` 这类桥接

但在真实工程中，仍有一类非常重要的接口无法挂上表：

- `Mapper extends BaseMapper<Entity>`
- Service 中直接调用：
  - `selectPage`
  - `selectList`
  - `selectOne`
  - `selectById`
  - `this.baseMapper.xxx(...)`
  - `getBaseMapper().xxx(...)`

这类调用没有显式 SQL，也没有 XML/注解 SQL，但人可以稳定地从：

- `Mapper extends BaseMapper<Entity>`
- `Entity 上的 @TableName`

反推出访问的物理表。

典型例子：

- `api:GET /assetManagement/selectAMProductNetWorthAnalysis`

这条 API 当前能识别到：

- Controller
- Service
- Mapper 调用

但由于查询由 MyBatis-Plus 框架自动生成，而不是源码中的显式 SQL，当前系统无法把它归并为表血缘。

## 2. Goal

新增一层 **MyBatis-Plus 通用 CRUD 静态推导能力**，在不执行框架、不猜测表名的前提下，把常见 `BaseMapper<Entity>` CRUD 调用稳定归并回表级血缘。

第一版目标：

- **读查询优先保证准确**
- 写操作做保守覆盖
- 仅在证据链完整时产出表

## 3. Non-Goals

第一版不做：

- 没有 `@TableName` 时根据实体名猜表名
- 根据 Wrapper 还原完整 SQL
- 根据 Wrapper 推断 join 进来的其他表
- 推断复杂 ORM 动态行为
- 推断列级/字段级血缘
- 推断运行时分支到底实际命中了哪一套数据源

## 4. Supported Evidence Chain

只有在满足以下证据链时，才允许产出表血缘：

1. 识别到 Mapper 接口
2. Mapper `extends BaseMapper<Entity>`
3. 能识别出 `Entity`
4. `Entity` 上存在 `@TableName("...")`

如果缺少其中任何一步：

- 不产出表
- 在诊断信息中保留 unresolved / missing evidence

## 5. First-Version Coverage

### 5.1 Read methods

第一版优先支持这些读查询：

- `selectPage`
- `selectList`
- `selectOne`
- `selectById`
- `selectBatchIds`
- `selectMaps`
- `selectCount`

这些统一推导为：

- `READS @TableName`

### 5.2 Write methods

第一版保守支持这些写操作：

- `insert`
- `updateById`
- `update`
- `deleteById`
- `delete`
- `deleteBatchIds`

这些统一推导为：

- `WRITES @TableName`

写操作会进入实现，但本轮测试重点仍放在读查询。

## 6. Required Real-World Patterns

第一版必须覆盖这些真实模式：

1. 字段注入 Mapper

```java
@Autowired
private RpAmFundRiskprofitMapper amFundRiskprofitMapper;
```

2. `this.baseMapper.xxx(...)`

3. `getBaseMapper().xxx(...)`

4. 一个 API 同时走两套 Service / Mapper / Table

例如：

- `RP_AM_FUND_RISKPROFIT`
- `frms.am_product_riskprofit`

按产品要求，第一版对此类接口应把 **两张表都挂出来**，而不是只保留一条。

## 7. Architecture

### 7.1 New static indexes

新增一层静态索引：

1. `Entity -> @TableName`
2. `Mapper -> Entity`
3. `Mapper -> physical table`

### 7.2 Reduction hook

在现有 Java reduction 过程中，如果识别到这些调用：

- `mapper.selectPage(...)`
- `mapper.selectList(...)`
- `this.baseMapper.selectOne(...)`
- `getBaseMapper().selectById(...)`

则不再等待显式 SQL，而是直接通过：

- `Mapper -> Entity -> @TableName`

产出表血缘。

### 7.3 Conservative behavior

所有推导都必须是静态、保守、可解释的：

- 有证据才产出
- 无证据则保持空
- 不猜表名

## 8. Data Flow

```mermaid
flowchart LR
    A["Mapper extends BaseMapper<Entity>"] --> B["Resolve Entity"]
    B --> C["Read @TableName"]
    C --> D["Build Mapper -> Table Index"]
    D --> E["Detect CRUD call in Service / Controller chain"]
    E --> F["Emit READS / WRITES table facts"]
    F --> G["Reduce into api_endpoint lineage"]
```

## 9. Diagnostics

为了避免“看起来像识别到了调用，但没有挂上表”的困惑，需要补这些可解释状态：

- `mapper_without_basemapper_entity`
- `entity_without_table_name`
- `crud_method_without_table_binding`

这些原因只在证据链缺失时记录。

## 10. Testing Strategy

至少覆盖：

1. `Mapper extends BaseMapper<Entity>` + `@TableName`
2. `selectPage` 读表
3. `selectList` 读表
4. `selectOne` / `selectById` 读表
5. `insert/update/delete` 写表
6. `this.baseMapper.xxx(...)`
7. `getBaseMapper().xxx(...)`
8. 一个 API 同时挂出两张表
9. 无 `@TableName` 时不产出表

## 11. Success Criteria

以真实接口为代表：

- `api:GET /assetManagement/selectAMProductNetWorthAnalysis`

第一版完成后，应至少能挂出：

- `RP_AM_FUND_RISKPROFIT`
- `frms.am_product_riskprofit`

并且 API 诊断里的：

- `read_table_count`

应大于 `0`。

## 12. Risks

### Risk 1: 误把非 CRUD 方法当成通用 CRUD

Mitigation:

- 只对白名单方法名生效

### Risk 2: Mapper 继承层级复杂

Mitigation:

- 第一版只覆盖明确的 `BaseMapper<Entity>`
- 更复杂继承放后续增强

### Risk 3: 一个接口同时命中多张表导致图膨胀

Mitigation:

- 这是当前产品要求的一部分
- 先完整展示，后续再考虑环境分支裁剪

## 13. Out of Scope for This Spec

以下能力继续留在后续范围，不纳入本轮：

- Oracle 特殊语法完整解析
- 复杂 `CASE` / 复杂子查询模板化展开
- 完整 ORM 运行时语义执行
