# hiaok — 轻量级权限中心

[English](readme-en.md) · [日本語](readme-jp.md) · **中文** · 架构设计文档（英文）：[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

DDD 四层 + 事件驱动 + 写主读从。Python 3.12 · FastAPI · SQLAlchemy 2 (asyncpg) · Alembic · Expression · Redis（缓存 / Streams）· Kafka

提供：组织、租户、用户、用户组、项目、角色、权限、菜单、部门、员工、系统配置、审计日志的管理接口，以及登录鉴权（Bearer token + 权限码）和多语言错误消息（en / zh / ja）。

本文按主题组织：

1. [快速开始](#1-快速开始)
2. [如何使用这套 DDD 框架](#2-如何使用这套-ddd-框架)
3. [如何鉴权](#3-如何鉴权)
4. [Kafka 的使用方式](#4-kafka-的使用方式)
5. [Redis 的使用方式](#5-redis-的使用方式)
6. [国际化（i18n）](#6-国际化i18n)
7. [接口约定](#7-接口约定)
8. [配置参考](#8-配置参考)
9. [测试与注意事项](#9-测试与注意事项)

---

## 1. 快速开始

```bash
uv sync
docker compose up -d postgres-master postgres-slave redis   # 只起基础设施
uv run alembic upgrade head                                  # 迁移永远走主库
uv run hiaok                                                 # API  http://localhost:8000/docs
uv run hiaok worker                                          # 消费者（APP_CONSUME_EVENTS=false 时需要）

docker compose up -d --build                                 # 全部容器：主从 + redis + migrate + api + worker
docker compose --profile kafka up -d --build                 # 加 Kafka，并设 APP_BROKER=kafka
```

- 配置：`APP_ENV`（真实环境变量）选择 profile，读取 `.env` 再读 `.env.<APP_ENV>`，真实环境变量优先。完整列表见[配置参考](#8-配置参考)。
- 迁移：`uv run alembic revision --autogenerate -m "..."`。不使用触发器：`update_time` 由 SQLAlchemy `onupdate=func.now()` 在每条 UPDATE 中写入。改表后执行 `uv run python scripts/gen_db_doc.py` 重新生成 [`db.properties.md`](db.properties.md)（测试会校验它是否过期）。
- 首次使用没有任何用户，可以先用 `AUTH_ENABLED=false` 启动，创建组织、角色和管理员之后再打开认证（见[如何鉴权](#3-如何鉴权)）。

## 2. 如何使用这套 DDD 框架

### 2.1 分层与依赖方向

```
presentation → application → domain ← infrastructure          （各层都可以用 hiaok_core）
```

```
src/                              # 业务包（src 本身就是包）：包内用相对导入，tests / scripts 用 from src.domain ...
├─ main.py                        # CLI `hiaok`（API）| `hiaok worker`（消费者）；create_app() / lifespan
├─ domain/                        # 只依赖 hiaok_core，不依赖任何框架
│  ├─ entity/                     # 实体与聚合根（create 返回 Result，记录领域事件）；event.py = 全部领域事件
│  ├─ vo/  enum/                  # 值对象（构造即校验）、枚举
│  ├─ service/                    # 领域服务：tree（建树 / 防环）、authority（权限求并集）
│  └─ repository/                 # 仓储接口（Protocol）+ Page / PageQuery
├─ application/
│  ├─ config/                     # app / auth / database / redis / kafka 配置（pydantic-settings）
│  ├─ model/                      # 应用模型：XxxModel(from_domain/to_domain)、CreateXxx、UpdateXxx
│  ├─ service/                    # @master / @slave 应用服务（事务边界）
│  └─ usecase/                    # 柯里化用例 + 事件处理器 + 写命令处理
├─ infrastructure/
│  ├─ database/ do/ dao/ repository/   # 主从引擎、表对象 XxxDO、DAO（to_entity / to_do）、仓储实现
│  ├─ messaging/                  # EventBus：Redis Streams / Kafka / 内存；topics.py = Kafka 路由
│  ├─ cache/ security/ http/      # Cache（Redis / 内存）、PasswordHasher（scrypt）、HttpClient（httpx）
│  └─ resources.py  migrations/   # 进程级资源；Alembic
└─ presentation/
   ├─ endpoint/                   # 路由：RequestDTO + 注入的 usecase -> ResponseDTO
   ├─ schema/                     # DTO（pydantic，camelCase）与 application model 互转
   ├─ dependency/                 # 依赖注入：resources -> service -> usecase；鉴权守卫
   └─ exception.py middleware.py i18n.py messages.py security.py openapi.py
```

**hiaok-core** 是独立仓库 <https://github.com/solomanpan/hiaok-core>（facade 接口、异常、JSON / fp 工具、请求上下文），通过 uv 的 Git 依赖按 tag 引入。升级：改 `pyproject.toml [tool.uv.sources]` 里的 tag 后执行 `uv lock --upgrade-package hiaok-core`；两边同时开发时可临时改成本地 `path` 依赖，提交前改回 tag。

这些规则写在 `tests/unit/test_architecture.py`，违反时测试失败：层间依赖方向、每层允许的子目录、不使用 `port / PO / mapper` 命名、数据对象叫 `XxxDO`、每个 DAO 都有 `to_entity / to_do`、业务错误必须来自错误目录、`src` 内部用相对导入。

### 2.2 一次请求怎么走（以注册用户为例）

```
POST /v1/api/hiaok/user/add   {"requestId": "...", "reqInfo": {"orgUuid": "...", ...}}
  ApiRequest[UserRegisterRequest].req_info.to_command()     # schema: RequestDTO -> RegisterUser
  usecase: RegisterUserDep                                  # dependency: register_user(users, tenants, roles, hasher)
  register_user(...)(cmd)                                   # usecase: 柯里化，最后一个参数是请求数据
    RawPassword.create → tenants.get(@slave) → roles.list_by_uuids(@slave) → hash
    → users.register(@master)                               # service: 打开主库事务
        cmd.to_domain(uuid, hash) → User.register(...)      # domain: 校验 + 记录事件
        repo.save → DAO.to_do（user / user_detail / user_role）
        commit → after_commit: 发布 EntityCreated, UserRegistered
    .map(UserModel.from_domain)
  reply(result, UserResponse.of)                            # -> {"code": 0, "msg": "success", "resultInfo": {...}}
                                                            #    Error -> {"code": 400/403/404/409, "msg": ..., "errorCode": ...}
```

### 2.3 新增一个聚合（以 `Xxx` 为例）

1. **领域**：`domain/entity/xxx.py`——`create(...)` 返回 `Result[Xxx, DomainError]` 并记录事件；业务错误写进同文件的 `XxxErrors(ErrorCatalog)`；`domain/repository` 里加仓储接口。
2. **表**：`infrastructure/do/xxx.py`（`XxxDO`）→ `alembic revision --autogenerate` → `scripts/gen_db_doc.py`。
3. **DAO / 仓储**：`XxxDao(EntityDao[XxxDO, Xxx])` 实现 `to_entity` / `to_do`；单表聚合的仓储只需 `SqlRepository(db, XxxDao(db))`。
4. **应用**：`application/model/xxx.py`（`XxxModel` / `CreateXxx` / `UpdateXxx`）+ `application/service`（继承 `CrudService`，写方法 `@master`，读方法 `@slave`）。
5. **表现**：`presentation/schema/xxx.py`（DTO）+ `presentation/dependency` 注册 service 与用例 + `presentation/endpoint/xxx.py` 路由。
6. **写接口登记**：在 `presentation/dependency/command.py` 的 `build_write_handlers` 里加 handler（标准 CRUD 一行 `_crud(...)`）；`test_write_handlers.py` 检查接口和 handler 一一对应。
7. **Kafka 路由**：在 `infrastructure/messaging/topics.py` 给新实体和事件配 topic（没配测试会失败）。
8. **鉴权与翻译**：接口加 `dependencies=[has_permission("xxx:add")]`；错误文案加到 `presentation/messages.py`（缺翻译测试会失败）。

> **所有接口都已鉴权**（`<资源>:<接口>`，如 `user:add`；`user:*` 覆盖整个资源，`*` 为平台超级权限，可操作任意组织）。开放接口：`auth/login`、`auth/captcha`、`user/register`（受验证码保护；带 `roleUuids` 需要 `user:assign-roles`）和 `/health`。新建组织的 `ORG_ADMIN` 角色会获得组织内所有资源的 `<资源>:*`（不含 `*`）。引导：先用 `AUTH_ENABLED=false` 创建第一个组织/管理员，或使用 `AUTH_PLATFORM_ORG_UUID` 组织中拥有 `*` 的用户登录。


也可以用 `codegen/` 里的元模板（jinja2）按规格文件生成以上骨架，见 [codegen/README.md](codegen/README.md)。

### 2.4 各层怎么写

**端点**：请求体类型和返回类型写在函数签名里，FastAPI 据此校验并生成 Swagger。所有接口都是 `POST`，成功与否用 `code` 表示，所以不需要 `status_code`。

```python
@router.post("/add", dependencies=[has_permission("role:add")])
async def create_role(
    request: ApiRequest[RoleCreateRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(await submitter.create("Role", request.request_id, info.org_uuid, info.to_command()))
```

**依赖注入**（`presentation/dependency/`）：全部是 FastAPI `Depends`，分三层：`resources.py`（`app.state` 上的进程级资源）→ `service.py`（仓储实现注入应用服务）→ `usecase.py`（服务注入用例）。端点只声明需要的用例，例如 `usecase: RegisterUserDep`。标准 CRUD 用 `crud_usecases(service, Model.from_domain)` 一组注册，组合用例单独注册。

**用例**：柯里化函数，依赖在前、请求数据在最后，用 `AsyncResult` 链式组合（`bind / map / ensure`），返回 `Result`，不抛业务异常。

**错误目录**：业务错误统一声明一次（类别 + 错误码 + 文案模板），不要在代码里临时拼 `conflict(...)`：

```python
class RoleErrors(ErrorCatalog):
    system_role = ErrorSpec.conflict("system_role", "system role '{code}' cannot be deleted")


return RoleErrors.system_role.err(code=self.role_code)  # Result 风格
RoleErrors.system_role.raise_(code=...)  # 必须抛异常时
```

跨聚合的用例规则在 `application/usecase/errors.py`（`UseCaseErrors`）；通用的 `not_found(entity, id)` 直接使用。

**写主读从**：

```python
class RoleService(CrudService[Role]):
    @slave                      # 读：从库，只读事务
    async def get(...): ...

    @master                     # 写：主库；Ok -> commit，Error/异常 -> rollback
    async def grant_permissions(...): ...
```

| 场景 | 行为 |
|---|---|
| 最外层被装饰的调用 | 打开会话（主库或从库） |
| `@slave` 嵌套在 `@master` 内 | 加入主库会话：读到自己刚写的数据 |
| `@master` 嵌套在 `@slave` 内 | 抛出 `DataSourceRoutingError` |
| 返回 `Error(...)` | 只有根作用域决定：回滚，`after_commit` 不执行 |
| `@slave` 里写数据 | 驱动层只读，数据库直接拒绝 |
| 领域事件 | 只在根事务提交成功后发布 |

多聚合原子写放在编排服务里：`ProvisioningService.provision`（组织 + 详情 + 默认租户 + ORG_ADMIN + 默认配置）、`OnboardingService.onboard`（入职 + 开账号 + 关联），外层 `@master` 一个事务，内层服务的 `@master` 自动加入。仓储 / DAO 从不自己开会话，在被装饰方法之外调用会抛 `NoActiveScopeError`；同一作用域内不要 `asyncio.gather` 多个仓储调用（共享一个 AsyncSession）。

**测试数据**：`tests/factories.py`（polyfactory）：`RoleFactory.build(...)`、`PermissionFactory.batch(3)`。工厂直接构造实体（不走校验、不产生事件）；要测校验或事件本身时用聚合的 `create` / `register`。

## 3. 如何鉴权

### 3.1 流程

```
POST /auth/login {orgUuid, tenantUuid, username, password}
  → 校验用户（启用）、密码（scrypt）、租户（启用且未过期）
  → 生成随机 token，会话 {userUuid, orgUuid, tenantUuid} 存入缓存（TTL = AUTH_SESSION_TTL_SECONDS，默认 2 小时）
  ← accessToken

之后每个请求：Authorization: Bearer <token>
  中间件   token → 会话 → 填请求上下文（operator = 用户 uuid、org、tenant）；审计字段 opr 因此自动是登录用户
  守卫     has_permission("role:add") / has_role("admin") / authenticated()
           会话 → 权限（用户 → 启用的角色 → 权限码；按用户缓存）→ 判断 → 通过 / 401 / 403
```

token 是不含任何信息的随机串，缓存里只保存它的 SHA-256；退出登录（`/auth/logout`）删除会话即可立即失效。

### 3.2 在接口上声明

```python
@router.post("/add", dependencies=[has_permission("role:add")])  # 任一权限码；role:* 覆盖 role:add，* 覆盖全部
@router.post("/list", dependencies=[has_role("admin", "auditor")])  # 任一角色
@router.post("/me", dependencies=[authenticated()])  # 只要登录
async def handler(principal: PrincipalDep): ...  # 需要知道是谁时
```

- **权限码约定**：`<资源>:<动作>`，例如 `role:grant-permissions`、`menu:move`；动作和路由一一对应。角色里的权限码在权限表里配置，改授权不需要改代码，所以接口优先用 `has_permission`，`has_role` 只留给"超级管理员"这类少数场景。
- **租户隔离**：请求体里的 `reqInfo.orgUuid` 不是调用者所属组织时返回 403 `org_mismatch`。`AUTH_PLATFORM_ORG_UUID` 指定的平台组织、以及拥有 `*` 的用户可以跨组织。
- **返回**：未登录 / token 无效或过期 → `code` 401（`unauthenticated`）；缺权限 → 403（`permission_denied` / `role_denied`）。HTTP 状态保持 200，和其他业务错误一致。
- **开关**：`AUTH_ENABLED=false` 时所有守卫放行，`X-Operator` 请求头决定操作人（本地调试、首次初始化用）。
- **验证码**（默认关闭）：`AUTH_CAPTCHA_ENABLED=true` 时，`POST /auth/login` 和 `POST /user/register` 必须带 `captchaId` + `captchaCode`。一次性图片从 `POST /auth/captcha` 获取（有效期 `AUTH_CAPTCHA_TTL_SECONDS`，默认 120 秒；返回 `{required, captchaId, image, expiresIn}`，关闭时 `required:false`）；答错一次即作废。
- **跨域**：设置 `APP_CORS_ORIGINS`（逗号分隔，如 `http://localhost:5173,tauri://localhost`），前端 [hiaok-web](https://github.com/solomanpan/hiaok-web)（Web / 桌面 / 移动）才能调用 API。

### 3.3 权限与菜单怎么算

权限 = 用户 → 启用的角色 → 权限码并集；菜单 = 同样的角色 → 菜单并集，只保留启用且可见的，再组成树（`domain/service/authority.py`）。

- `/auth/me` 返回 `roleCodes`、`permissionCodes` 和菜单树，前端登录后调一次渲染侧边栏。**菜单只决定前端显示什么，接口是否放行永远由各自的守卫决定。**
- 角色、权限码按用户缓存 `AUTH_AUTHORITY_TTL_SECONDS`（默认 60 秒）；用户、用户组、角色、权限的增删改事件和角色授权 / 分配菜单事件会让整个组织的缓存立即失效（实现见 [Redis 的使用方式](#5-redis-的使用方式)）。菜单树不缓存，`/auth/me` 每次查库。

### 3.4 现状与待办

- 目前 `role`、`menu` 和 `/auth/*` 接入了守卫；其他资源还没有。`tests/unit/presentation/test_security.py` 的 `UNGUARDED_YET` 列出尚未接入的资源，新增接口忘记加守卫会让测试失败；资源接完守卫后，把它从该集合里删掉。
- `/user/authorities` 目前没有守卫，任何人都能查任何用户的权限，应尽快补上。
- 首个管理员需要手工初始化（`AUTH_ENABLED=false` 启动后注册）。

## 4. Kafka 的使用方式

### 4.1 什么时候用

`APP_BROKER=kafka` 时，Kafka 是**事件总线**：承载两类消息

1. **写命令**（`WriteRequested`）：接口只发布不写库，消费者执行（见 4.5）。
2. **领域事件**（`EntityCreated`、`UserRegistered`、`RolePermissionsChanged`…）：事务提交后发布，消费者写审计日志、驱逐缓存。

开发和测试可以用 `APP_BROKER=memory`（进程内，写请求在 `publish` 里同步执行，无需任何外部服务），小规模部署用默认的 Redis Streams（见第 5 节）。

### 4.2 Topic 设计

按业务域拆 5 个 topic，写命令和它引发的领域事件走同一个 topic：

| topic（默认前缀 `hiaok`） | 承载的实体 | 死信 topic |
|---|---|---|
| `hiaok.organization` | 组织、租户、项目 | `hiaok.organization.dlq` |
| `hiaok.identity` | 用户、用户组 | `hiaok.identity.dlq` |
| `hiaok.authorization` | 角色、权限、菜单 | `hiaok.authorization.dlq` |
| `hiaok.hr` | 员工、部门 | `hiaok.hr.dlq` |
| `hiaok.config` | 系统配置 | `hiaok.config.dlq` |

- 路由表在 `infrastructure/messaging/topics.py`（`Topic`、`TOPIC_OF_ENTITY`、`TOPIC_OF_EVENT`、`topic_of`）。新增实体或事件没配路由会抛 `UnroutableEvent`，测试也会失败。
- **消息 key = 聚合 id**（写命令用目标 uuid）：同一个聚合的消息进同一个分区，保证顺序。
- **消息体**：`{"event_type": "...", "payload": {...}}` 的 JSON；header 带 `event_type`。无法识别的 `event_type`（更新版本产生的事件）直接跳过。

### 4.3 发送

生产者：`acks=all` + `enable_idempotence=True`，`send_and_wait`（发送成功才返回）。

```python
# 接口层只需要这一行，其余由总线完成
await submitter.update("Role", request.request_id, org_uuid, uuid, command)
#  → WriteRequested(entity_type="Role", command_type="Role.update", target_uuid=uuid, payload=...)
#  → topic_of(event) = hiaok.authorization，key = uuid
```

### 4.4 消费

每个 topic 一个消费者，group = `<KAFKA_GROUP_ID>.<topic>`（如 `hiaok.authorization`），`auto_offset_reset=earliest`，**手动提交 offset**：

```
取消息 → 反序列化 → 找订阅者 → 执行（失败重试 3 次，间隔 0.2s / 0.4s / 0.6s）
   ├─ 成功（或未知事件）→ 提交 offset
   └─ 仍失败（或无法反序列化）→ 原样发到 <topic>.dlq，header 加 source_topic / source_partition / source_offset → 提交 offset
```

只有处理成功或进入死信之后才提交，所以不丢消息；一条坏消息也不会阻塞整个 topic。**至少一次投递**：消费者必须幂等（写命令用 `requestId` 派生的结果记录去重，见 4.5）。

领域事件的消费者（`application/usecase/event_handler.py`）：

| 事件 | 处理 |
|---|---|
| 所有领域事件（除 `WriteRequested`） | 写 `sys_log` 审计，`log_uuid` 由 `event_id` 派生，重放安全 |
| `SysConfigChanged` | 驱逐配置缓存 |
| 用户 / 用户组 / 角色 / 权限的增删改，角色授权、分配菜单、用户分配角色 | 使该组织的权限缓存失效 |

### 4.5 异步写入的完整流程

`add / update / delete` 和专有写动作（授权、移动、入职 / 离职 / 调动…）不直接写库：

```
POST /v1/api/hiaok/role/update          {requestId, reqInfo}
  endpoint:  WriteSubmitter.update("Role", ...) → 发布 WriteRequested（key = 目标 uuid）→ 立即返回
             {"code": 0, "resultInfo": {"requestId": "...", "uuid": "...", "status": "accepted"}}
  consumer:  handle_write → handlers["Role.update"] → 原来的 usecase → service(@master) → 入库
             成功：同一事务里写一条结果记录（sys_log, log_type=command）
             业务失败（重复编码、角色不存在…）：回滚并记录失败，不重试
             异常（数据库不可用…）：向上抛，总线重试 3 次，仍失败进死信
  查询结果:  POST /v1/api/hiaok/log/get-by-request  {orgUuid, targetRequestId}
             → status = success | failed | pending（code / msg / errorCode 与同步时一致，msg 按 Accept-Language 翻译）
```

- **新增时的 uuid** 由 `requestId` 派生（`application/service/ids.py`），接口能在实体创建前就返回 uuid；消费者按同一序列生成 id，重复投递也生成同样的 id。
- **幂等**：结果记录的 `log_uuid` 由 `requestId` 派生，已有记录就跳过；结果记录和业务写入在同一个事务里，要么都成功要么都回滚。同一个 `requestId` 重复提交只会执行一次。
- `pending` 表示：还没消费、正在重试，或已进死信。进死信的命令需要人工处理（见 4.7）。
- **仍然同步的接口**：用户注册（`/user/add`）、修改密码、员工入职（`/employee/add`，可带账号）。它们带明文密码，不能写进 Kafka（消息会落盘保留）。
- 新增写接口 = 在 `build_write_handlers` 里登记 handler。

### 4.6 配置

| 环境变量 | 默认 | 说明 |
|---|---|---|
| `APP_BROKER` | `redis` | `redis` \| `kafka` \| `memory` |
| `APP_CONSUME_EVENTS` | `true` | `false`：该进程只发布不消费，另起 `hiaok worker` 消费，可水平扩展 |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9094` | 容器内用 `kafka:9092` |
| `KAFKA_TOPIC_PREFIX` | `hiaok` | topic = `<prefix>.<domain>` |
| `KAFKA_GROUP_ID` | `hiaok` | 消费组 = `<group_id>.<domain>` |
| `KAFKA_DLQ_SUFFIX` | `.dlq` | 死信 topic 后缀 |
| `KAFKA_CREATE_TOPICS` | `true` | 启动时创建 10 个 topic（5 个业务 + 5 个死信），已存在则忽略；生产环境建议关闭并由运维创建 |
| `KAFKA_NUM_PARTITIONS` | `3` | 创建 topic 时的分区数 |
| `KAFKA_REPLICATION_FACTOR` | `1` | 创建 topic 时的副本数，生产环境按 broker 数调整 |

部署形态：

```
        ┌─ api（APP_CONSUME_EVENTS=false）──publish──▶ Kafka ◀──consume── worker × N（hiaok worker）
 客户端 ─┤
        └─ 或单进程：api 同时消费（APP_CONSUME_EVENTS=true，默认）
```

同一个 group 的 worker 越多，分区被分摊得越均匀；并行度上限是分区数。

### 4.7 运维

- **看死信**：消费 `hiaok.<domain>.dlq`，header 里的 `source_topic / source_partition / source_offset` 指向原消息。消息体和原消息一致，修好原因后重新发回原 topic 即可（消费是幂等的）。
- **看某个写请求的结果**：`/log/get-by-request`；`pending` 时先查消费者日志，再查对应 `.dlq`。
- **加一个 topic**：① `Topic` 枚举加成员；② `TOPIC_OF_ENTITY` 配实体（有领域事件时 `TOPIC_OF_EVENT` 配事件）；③ 写命令在 `build_write_handlers` 登记 handler；④ `test_topics.py` 补路由用例；⑤ 生产环境先创建 topic 和 `.dlq`。消费者和 group 按枚举自动生成，不需要改总线代码。
- 本地试 Kafka：`docker compose --profile kafka up -d --build`，设 `APP_BROKER=kafka`；集成测试在 Kafka 不可达时自动跳过。

## 5. Redis 的使用方式

Redis 有两个独立的用途，用不同的配置开关：

| 用途 | 开关 | 说明 |
|---|---|---|
| 事件总线（Streams） | `APP_BROKER=redis`（默认） | 与 Kafka 二选一 |
| 缓存 | `APP_CACHE=redis`（默认） | `APP_CACHE=memory` 用进程内缓存（单机 / 测试，多副本之间不共享） |

### 5.1 缓存

所有 key 自动加前缀 `REDIS_CACHE_PREFIX`（默认 `hiaok:`），默认 TTL `REDIS_CACHE_TTL_SECONDS`（300 秒）。接口只有 `get / set(ttl) / delete`，由 `hiaok_core.facade.Cache` 定义。

| key（不含前缀） | 内容 | TTL | 失效方式 |
|---|---|---|---|
| `sys_config:<org>:<key>` | 系统配置（读穿缓存，`SysConfigService.get_by_key`） | 300 秒 | 任何写入提交后 `SysConfigChanged` 事件驱逐 |
| `session:<sha256(token)>` | 登录会话 `{userUuid, orgUuid, tenantUuid}` | `AUTH_SESSION_TTL_SECONDS`（2 小时） | 退出登录删除；过期自动消失 |
| `authz:<org>:<版本>:<user>` | 用户的角色码 + 权限码 | `AUTH_AUTHORITY_TTL_SECONDS`（60 秒） | 见下 |
| `authz_ver:<org>` | 该组织的权限缓存版本号 | 1 天 | 相关事件到来时改成新值 |

**权限缓存怎么整组失效**：key 里带组织的版本号。用户、用户组、角色、权限的变更事件到来时，只改写 `authz_ver:<org>`，该组织所有用户的旧 key 立刻读不到（等自然过期），不需要扫描删除。

### 5.2 事件总线（Redis Streams）

`APP_BROKER=redis` 时，`infrastructure/messaging/redis_stream.py`：

| 项 | 实现 |
|---|---|
| 发布 | `XADD hiaok-events * data <json>`，`MAXLEN ~ 100000`（近似裁剪） |
| 消费 | consumer group `hiaok`，consumer `consumer-1`，`XREADGROUP ... >` 每次最多 50 条，阻塞 1 秒 |
| 建组 | 启动时 `XGROUP CREATE ... $ MKSTREAM`，已存在忽略；**只消费建组之后的新消息** |
| 确认 | 处理成功（或未知事件）才 `XACK` |
| 重试 | 进程内重试 3 次（0.2s / 0.4s / 0.6s） |
| 失败 | 不 `XACK`，消息留在 PEL（待处理列表） |

和 Kafka 的差异（选型时要知道）：

- **只有一个 stream、一个消费组**，不按业务域拆分，也没有死信队列。处理失败的消息留在 PEL，用 `XPENDING hiaok-events hiaok` 查看，用 `XAUTOCLAIM` 重新认领或手工转存。
- 同一个 group 内有多个 consumer 时，消息被分摊；consumer 名默认固定为 `consumer-1`，多个 worker 副本需要给每个副本设置不同的 `REDIS_CONSUMER_NAME`。
- 没有 key 分区，因此**不保证同一聚合的消息顺序**（多个 consumer 并行时）；需要严格顺序、更大吞吐或更长保留时间时选 Kafka。
- 写命令的流程、幂等和结果查询与 Kafka 完全一致。

### 5.3 配置

| 环境变量 | 默认 | 说明 |
|---|---|---|
| `REDIS_URL` | `redis://localhost:6379/0` | 缓存和 Streams 共用 |
| `REDIS_STREAM` | `hiaok-events` | stream 名 |
| `REDIS_CONSUMER_GROUP` | `hiaok` | 消费组 |
| `REDIS_CONSUMER_NAME` | `consumer-1` | 多副本时每个副本设不同的值 |
| `REDIS_STREAM_MAXLEN` | `100000` | 近似最大长度 |
| `REDIS_CACHE_PREFIX` | `hiaok:` | 缓存 key 前缀（stream 不加前缀） |
| `REDIS_CACHE_TTL_SECONDS` | `300` | 缓存默认 TTL |

## 6. 国际化（i18n）

错误消息按调用方语言返回：`Accept-Language: zh-CN,zh;q=0.9,en;q=0.8` → 选 `q` 最大且受支持的语言（`en` / `zh` / `ja`），响应头带 `Content-Language`。都不支持时用 `APP_DEFAULT_LOCALE`（默认 `en`）。

- **错误码不变**：`code`、`errorCode` 永远相同，只有 `msg` 翻译；客户端应当用 `errorCode` 判断逻辑，`msg` 只用于展示。
- **原理**：业务错误是由目录里的英文模板 + 参数生成的值。展示时把消息匹配回它的错误规格（错误码和文本都要匹配），取出参数，填进 `presentation/messages.py` 里翻译后的模板；`entity`（如 `User` → `用户`）等词也会翻译。没有翻译的消息保持英文。
- **新增错误文案**：在错误目录里声明之后，到 `presentation/messages.py` 的 `TEMPLATES` 里加 `zh`、`ja` 两条（key 是英文模板）。`tests/unit/presentation/test_i18n.py` 会在缺翻译、占位符不一致、翻译对应的消息已不存在时失败。
- **新增一种语言**：`LOCALES` 加语言代码，`messages.py` 的每个条目加该语言；测试会列出缺失项。
- **范围**：接口的 `msg`（含异步写入的失败结果）、401 / 500 的固定文案。请求体格式校验的消息来自 pydantic，不翻译；Swagger 说明文字保持中文。

## 7. 接口约定

所有接口都是 `POST /v1/api/hiaok/<资源>/<动作>`，请求 `{requestId, reqInfo}`，响应 `{code, msg, resultInfo}`，字段 camelCase；组织用 `reqInfo.orgUuid`，目标资源用 `reqInfo.uuid`。

| 请求头 | 说明 |
|---|---|
| `Authorization: Bearer <token>` | 受保护接口必填（`POST /auth/login` 获取） |
| `Accept-Language` | `en` / `zh` / `ja`，决定 `msg` 的语言 |
| `X-Request-Id` | 链路追踪 id，原样回显在响应头；缺省自动生成 |
| `X-Operator` | 仅 `AUTH_ENABLED=false` 时使用 |

可预期的错误是 HTTP 200 + `code`：

| code | 含义 |
|---|---|
| 0 | 成功 |
| 400 | 业务校验失败，或请求体格式错误（`errorCode` = `invalid_request`） |
| 401 | 未登录 / token 失效（`unauthenticated`），或用户名密码错误（`invalid_credentials`） |
| 403 | 无权限（`permission_denied` / `role_denied`），或操作了不属于自己的组织（`org_mismatch`） |
| 404 | 资源不存在 |
| 409 | 状态冲突（重复编码、删除系统角色…） |
| 502 / 500 | 上游服务失败 / 未预期的系统错误（这两种是真实的 HTTP 状态；细节只写日志） |

列表接口在 `reqInfo` 里传 `offset`（默认 0）/ `limit`（默认 20，最大 200），`resultInfo` 为 `items / total / offset / limit`。

Swagger：`http://localhost:8000/docs` · ReDoc `/redoc` · `/openapi.json`；受保护接口带 Bearer 声明，右上角 Authorize 填入 token 即可调试。生产环境如不对外，设 `APP_DOCS_ENABLED=false`。

## 8. 配置参考

`APP_ENV` 选择 profile（`dev` Redis + 主 5432 / 从 5433；`test` 内存 + 单库；`docker` compose 内主从）。

| 前缀 | 变量 | 默认 |
|---|---|---|
| `APP_` | `NAME` `ENV` `HOST` `PORT` `LOG_LEVEL` | `hiaok` / `dev` / `0.0.0.0` / `8000` / `INFO` |
| | `BROKER` | `redis`（`kafka` \| `memory`） |
| | `CACHE` | `redis`（`memory`） |
| | `CONSUME_EVENTS` | `true` |
| | `DOCS_ENABLED` | `true` |
| | `DEFAULT_LOCALE` | `en`（`zh` \| `ja`） |
| `AUTH_` | `ENABLED` | `true` |
| | `SESSION_TTL_SECONDS` | `7200` |
| | `AUTHORITY_TTL_SECONDS` | `60`（1–86400） |
| | `PLATFORM_ORG_UUID` | 空 |
| `DB_` | `MASTER_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/hiaok` |
| | `SLAVE_URL` | 空（读也走主库） |
| | `POOL_SIZE` `MAX_OVERFLOW` `POOL_RECYCLE` `ECHO` | `10` / `20` / `1800` / `false` |
| `REDIS_` / `KAFKA_` | 见第 4、5 节 | |

## 9. 测试与注意事项

```bash
uv run pytest                          # 全部（集成测试在没起服务时自动跳过）
uv run pytest -m "not integration"
docker compose up -d redis && uv run pytest -m integration
uv run ruff check . && uv run ruff format --check . && uv run pyright
```

```text
tests/
├─ unit/domain/          # 值对象、聚合、树、授权规则
├─ unit/application/     # 写命令（幂等、失败记录）、事件处理
├─ unit/infrastructure/  # serde、内存总线、topic 路由、缓存、DAO 转换
├─ unit/presentation/    # 信封、异常映射、鉴权守卫、i18n、OpenAPI
├─ unit/test_architecture.py    # 分层与命名规则
└─ integration/          # 需要真实 Redis / Kafka，连不上自动 skip
```

- `user` 是 PostgreSQL 保留字。ORM 会自动加引号；手写 SQL 必须写 `"user"`。
- 从库有复制延迟：写完立刻读可能短暂读不到。异步写入时更要通过 `/log/get-by-request` 确认结果，而不是立刻回读。
- 事件在提交后发布，进程在两者之间崩溃会丢事件；需要严格保证时改为 transactional outbox。
- 进入死信的写命令会一直显示 `pending`，需要人工处理。

## 许可证

[MIT](LICENSE) © 2026 PAN JIE <sanbaikuai@gmail.com>
