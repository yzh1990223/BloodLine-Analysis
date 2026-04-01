# Java API 血缘增强设计

## 1. 背景

当前 BloodLine Analysis 已经具备：

- Spring MVC HTTP 路由识别
- Java 方法级事实模型
- 最小方法调用图
- 注解 SQL / 最小 XML Mapper SQL 提取
- API 节点到表的最小穿透能力

在真实工程 `/Users/nathan/Documents/resources/frms-src/main` 上，系统已经能识别大量 `api_endpoint` 节点，但真正挂接到表的比例仍然偏低。

截至本次设计前的真实扫描结果：

- `api_endpoint` 节点：795
- 带 `READS` 的 API 节点边：47
- 带 `WRITES` 的 API 节点边：3

这说明当前问题不在“有没有识别出 API 路由”，而在“Controller -> Service -> Impl -> Mapper/SQL -> Table”这条链的真实工程适配能力仍然不足。

基于对真实目录 `/Users/nathan/Documents/resources/frms-src/main` 的补充调研，还可以看到更具体的模式特征：

- `main/java` 中约有 `1807` 个 Java 文件
- 识别到 `211` 个 Controller，其中 `210` 个是 `@RestController`
- 路由方法注解以 `@PostMapping` 和 `@GetMapping` 为主：
  - `@PostMapping 526`
  - `@GetMapping 313`
  - `@RequestMapping 213`
- Service 注入几乎全是字段注入：
  - `@Autowired 535`
  - `@Resource 33`
- Service 层大量采用接口 + 实现类双层结构：
  - `254` 个 `*Service` 接口
  - `255` 个 `*ServiceImpl` 类
- 其中 `115` 个 `ServiceImpl` 直接 `extends ServiceImpl<Mapper, Entity>`
- Mapper / DAO 约 `386` 个，其中 `333` 个直接 `extends BaseMapper<...>`
- XML Mapper 约 `209` 个，其中带 `<if>/<foreach>/<where>/<set>/<trim>` 等动态标签的有 `132` 个
- 注解 SQL 虽然总量不高，但变体明显：
  - `@Select(value = "...")`
  - 多段字符串拼接
- 只有约 `200/386` 个 Mapper / DAO Java 文件存在同目录同名 XML，另有部分 XML 位于 `main/resources/mapper`

这些模式共同说明：真实工程里的主要难点，不是“多识别几种 Controller 注解”，而是“如何把字段注入、接口实现、多层 Service、MyBatis-Plus 继承式 CRUD、动态 XML 和注解 SQL 变体，稳定归并回表级事实”。

## 2. 目标

本轮增强目标是：

1. 提升真实 Spring 工程里 HTTP API 节点到表血缘的穿透率
2. 降低对简单命名猜测的依赖，更多基于声明类型和实现类关系做解析
3. 补强 Mapper / DAO / Repository 作为 SQL 事实承载点的桥接能力
4. 增加 API 血缘的诊断与可观测性，明确“断在哪一跳”

## 3. 非目标

本轮不包含：

- 字段级 API 血缘
- RPC / Feign / Dubbo 等非 HTTP 接口
- OpenAPI 文档联动
- 复杂运行时动态分派的完整语义解析
- 非 Java 服务框架的接口识别

## 4. 根因分析

### 4.1 路由识别不是主要瓶颈

当前 `java_controller_parser.py` 已能识别大量 Spring MVC 注解路由，数据库中 `api_endpoint` 节点数量已经证明这一层基本可用。

因此，后续增强不应继续把主要精力放在“多识别一些 Controller 路由”上。

### 4.2 Service 目标解析过于依赖命名猜测

当前 `java_lineage_reducer.py` 中的调用目标解析主要依赖：

- receiver 名称首字母大写转换
- 接口名 `IService` -> `ServiceImpl` / `Service` 的有限候选

这对简单 demo 有效，但对真实工程中的接口注入、多实现、命名不一致、抽象层封装等场景不够稳。

真实工程里已经观察到大量这类模式：

- Controller 注入接口，例如 `IXxxService`
- ServiceImpl 通过 `extends ServiceImpl<...>` 获得方法体，而不是在源码里直接声明
- Controller 直接调用 `save / getById / updateById / removeById / selectPage` 这类继承方法

典型样例包括：

- [FiDepositController.java](/Users/nathan/Documents/resources/frms-src/main/java/com/cicc/frms/client/app/controller/fi/FiDepositController.java#L30)
- [RpMappingService.java](/Users/nathan/Documents/resources/frms-src/main/java/com/cicc/frms/client/app/service/fi/RpMappingService.java#L11)
- [RpMappingServiceImpl.java](/Users/nathan/Documents/resources/frms-src/main/java/com/cicc/frms/client/app/service/fi/impl/RpMappingServiceImpl.java#L15)

### 4.3 方法调用图仍然是最小图

当前 `java_call_graph.py` 基于正则抽取：

- `receiver.method()`
- `localMethod()`

它提供的是最小可用调用图，但还不能稳定覆盖：

- 接口字段调用
- 构造注入对象调用
- 父类 / 抽象类转发
- 链式调用后的方法目标
- 部分带泛型与复杂签名的方法

### 4.4 SQL 承载点与上层调用链的桥接还不够强

当前 SQL 事实主要来自：

- Java 字符串 SQL
- MyBatis 注解 SQL
- 同 stem XML Mapper 的最小静态 SQL

但真实业务里很多 API 方法本身不含 SQL，而是：

- Controller 调 Service
- Service 调 Repository / DAO / Mapper
- Mapper / XML 才真正承载 SQL

如果这条桥接链没有被稳定接通，API 节点就会停留在“已识别路由，但无表边”的状态。

真实工程里尤其明显的几类漏点是：

- `BaseMapper` / `IService` / `ServiceImpl` 继承式 CRUD
- `LambdaQueryWrapper / QueryWrapper / LambdaUpdateWrapper` 这类 Wrapper DSL
- `@Select(value = "...")`、多段字符串拼接注解 SQL
- 动态 XML Mapper（`<if>`、`<foreach>`、`<where>`）
- 非 sibling XML（位于 `resources/mapper`）

典型样例包括：

- [RpCountryRiskExposureUploadServiceImpl.java](/Users/nathan/Documents/resources/frms-src/main/java/com/cicc/frms/client/app/service/countryRisk/impl/RpCountryRiskExposureUploadServiceImpl.java#L40)
- [RpCountryRiskExposureUploadMapper.java](/Users/nathan/Documents/resources/frms-src/main/java/com/cicc/frms/client/app/mapper/countryRisk/RpCountryRiskExposureUploadMapper.java#L17)
- [RpCountryRiskExposureUploadMapper.xml](/Users/nathan/Documents/resources/frms-src/main/java/com/cicc/frms/client/app/mapper/countryRisk/RpCountryRiskExposureUploadMapper.xml#L3)
- [CommRiskreportpublishlogMapper.java](/Users/nathan/Documents/resources/frms-src/main/java/com/cicc/frms/client/app/mapper/risk/CommRiskreportpublishlogMapper.java#L19)
- [ClientInfoMapper.xml](/Users/nathan/Documents/resources/frms-src/main/java/com/cicc/frms/client/app/mapper/client/ClientInfoMapper.xml#L19)
- [RmEDSFtMatchResultMapper.xml](/Users/nathan/Documents/resources/frms-src/main/java/com/cicc/frms/client/app/mapper/eds/RmEDSFtMatchResultMapper.xml#L3)

### 4.5 当前缺少失败可观测性

当某个 API 节点没能穿透到表时，系统目前无法明确告诉我们：

- 路由是否识别成功
- Controller 方法是否识别成功
- receiver 是否成功绑定到声明类型
- 接口是否成功匹配实现类
- 目标方法是否有方法级事实
- 方法级事实是否含 SQL/表

这会显著增加后续增强与排障成本。

## 5. 设计原则

### 5.1 优先增强真实工程命中率，而不是继续扩路由种类

后续增强优先级应放在：

- 调用链穿透
- SQL 承载点桥接
- 可观测性

而不是继续扩更多 HTTP 注解变体。

### 5.2 优先基于声明类型、类索引和实现类索引做解析

对 receiver 调用目标的解析，应从：

- 名称猜测优先

升级为：

- 字段声明类型优先
- 类 / 接口索引优先
- 实现类解析优先
- receiver 名称猜测作为 fallback

### 5.3 unresolved 不应静默吞掉

任何无法穿透到表的 API 节点，都应尽量保留诊断状态，便于后续观察和增量优化。

## 6. 方案拆分

### 方向一：增强 Spring 注入与实现类绑定

目标：让 `Controller -> Service -> Impl` 更稳定落到真实实现类。

增强点：

- 统一支持字段注入与构造注入的依赖抽取
- 从字段声明类型中识别接口类型
- 建立接口到实现类的索引
- 唯一实现类时自动绑定
- 多实现类时保守标记 unresolved，而不是乱猜
- 对 `extends ServiceImpl<Mapper, Entity>` 这种常见模式补“继承式 CRUD”桥接

预期收益：

- 提升 Controller 到业务实现类的命中率
- 显著增加有表边的 API 节点数量

### 方向二：增强调用目标解析与跨类方法图

目标：从“最小调用图”升级到更接近真实工程的跨类方法图。

增强点：

- 建立模块级方法索引
- 用 `声明类型 + 模块索引 + 实现类索引` 定位 receiver 目标
- 增强本地方法、跨类方法和实现类方法的解析稳定性
- 对无法解析的调用显式记录 unresolved 原因

预期收益：

- 降低调用链中断的概率
- 减少因为方法目标定位失败导致的 API 空节点

### 方向三：增强 Mapper / DAO / Repository 事实桥接

目标：让 SQL 承载点更稳地向上归并到 Controller/API。

增强点：

- 强化 Mapper 接口到注解 SQL / XML SQL 的绑定
- 支持 `value = "..."` 和多段字符串拼接注解 SQL
- 强化 Repository / DAO 命名模式识别
- 把“接口方法承载 SQL”与“实现类方法承载 SQL”统一抽象成方法级事实来源
- 当 Mapper 是接口且无实现体时，允许直接作为 SQL 事实终点
- 扩展 XML 查找范围，支持 sibling XML 之外的 `resources/mapper` 常见布局

预期收益：

- 让更多 Service -> Mapper 链路真正连到表
- 提升 API 节点的读写表覆盖率

### 方向四：增加 API 血缘诊断与可观测性

目标：明确每个 API 节点为什么穿透成功或失败。

增强点：

- 为 API 节点增加最小诊断摘要
- 记录：
  - `route_parsed`
  - `controller_method_parsed`
  - `receiver_bound`
  - `impl_resolved`
  - `method_fact_found`
  - `sql_fact_found`
  - `table_count`
- 对 unresolved 场景增加原因分类，例如：
  - `unresolved_receiver_type`
  - `multiple_impl_candidates`
  - `missing_method_fact`
  - `missing_sql_fact`

预期收益：

- 后续增强不再盲改
- 可以基于真实 unresolved 原因做增量迭代

## 7. 推荐实施顺序

1. 方向一：增强 Spring 注入与实现类绑定
2. 方向二：增强调用目标解析与跨类方法图
3. 方向三：增强 Mapper / DAO / Repository 事实桥接
4. 方向四：增加 API 血缘诊断与可观测性

原因：

- 方向一和方向二直接决定 Controller 能否稳定穿透到业务实现层
- 方向三补的是 SQL 承载点桥接
- 方向四负责把增强结果可视化和可诊断化

## 8. 测试策略

需要增加三类测试：

### 8.1 解析器单元测试

覆盖：

- 接口注入 -> 唯一实现类绑定
- 多实现类 unresolved
- Mapper 接口 + 注解 SQL
- Mapper 接口 + XML SQL
- 构造注入 / 字段注入场景

### 8.2 归并测试

覆盖：

- Controller -> Service -> Impl -> Mapper -> Table
- Controller -> Service -> Repository -> Table
- API 节点读写表集合归并

### 8.3 真实样例回归

基于真实工程模式补少量 fixture，验证：

- 至少一批真实风格 API 节点从无表边提升到有表边
- unresolved API 节点能给出合理原因分类

## 9. 风险与控制

### 风险一：接口多实现导致误归并

控制：

- 第一版只对唯一实现自动绑定
- 多实现时保守 unresolved

### 风险二：调用图过度复杂，误把无关链路并进来

控制：

- 只扩展最小必要的跨类图
- 不做全语言语义分析
- 每一步都配回归测试

### 风险三：增加可观测性后数据体过大

控制：

- 第一版只保留最小诊断摘要
- 不直接保存完整调用树

## 10. 完成标准

当以下条件满足时，本轮增强可视为完成：

- 真实工程中 API 节点挂表率明显提升
- 接口注入 / 实现类绑定已比当前稳定
- Mapper / DAO / Repository 事实桥接能力增强
- unresolved API 节点可看到明确失败原因分类
- 相关测试与文档同步更新
