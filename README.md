# hiaok — 轻量级权限中心

DDD 四层 + 事件驱动 + 写主读从。Python 3.12 · FastAPI · SQLAlchemy 2 (asyncpg) · Alembic · Expression · toolz · Redis Streams / Kafka

## 目录结构

```
hiaok/                                                   # 项目根
├─ Dockerfile · docker-compose.yml · docker/postgres/    # 容器、PG 主从复制脚本
├─ pyproject.toml                                        # 依赖（hiaok-core 走 Git tag）+ [tool.alembic] + ruff/pyright/pytest
├─ codegen/                                               # 元模板（jinja2）+ 模块规格，scripts/codegen.py 生成代码，见 codegen/README.md
├─ db.properties.md                                      # 全量建表 SQL（scripts/gen_db_doc.py 生成）
└─ src/hiaok_core/
│     ├─ facade/          # 外部能力接口：Cache, EventBus, TransactionManager, PasswordHasher, IdGenerator, HttpClient
│     ├─ exception.py     # DomainError（Result 里的值）+ HiaokError / DomainException / HttpClientError（可抛出）
│     ├─ json.py          # JSON 编解码（datetime / Enum / set / dataclass）
│     ├─ fp.py            # curry, AsyncResult 链式, sequence
│     └─ context.py       # 请求 / 消息上下文（操作人、trace id）
└─ src/                                                 # 业务包（src 本身就是包）：包内用相对导入 from ..domain ...，包外（tests/scripts）用 from src.domain ...
   ├─ __init__.py · main.py   # CLI `hiaok` (API) | `hiaok worker`；create_app() / FastAPI lifespan
   ├─ domain/                 # 只依赖 hiaok_core，不依赖任何框架
   │  ├─ entity/          # 实体（聚合根也是实体）：Organization, Tenant, User, Role, Menu …, OrgDetail, UserDetail, SysLog
   │  │                   # base.py: Entity / AggregateRoot；event.py: 领域事件（基类 + 通用 CRUD 事件 + 业务事件）
   │  ├─ vo/     # ValueObject, Audit, Code, Username, Email, PhoneNumber, RawPassword, RoleAssignment
   │  ├─ enum/            # Status, RoleType, PermType, MenuType, ConfigValueType, LogType
   │  ├─ service/         # 领域服务：tree.py（建树/防环）, authority.py（权限求并集）
   │  └─ repository/      # 仓储接口（Protocol）+ Page / PageQuery
   ├─ application/
   │  ├─ config/          # app / database(主从) / redis / kafka 配置
   │  ├─ model/           # 应用模型：XxxModel(from_domain/to_domain), CreateXxx(to_domain), UpdateXxx(apply_to)
   │  ├─ service/         # @master / @slave 应用服务（事务边界），调用 domain 仓储接口
   │  └─ usecase/         # 柯里化用例（调用 service）+ 事件处理器
   ├─ infrastructure/
   │  ├─ database/        # RoutingDatabase（主从两引擎）, SqlAlchemyTransactionManager, ORM Base
   │  ├─ do/              # 17 张表的数据对象 XxxDO
   │  ├─ dao/             # 表级访问 + 转换：EntityDao.to_entity(do) / to_do(entity, do=None)；LinkDao 处理关联表 diff
   │  ├─ repository/      # 仓储实现（DAO 组装聚合 + savepoint + 唯一冲突 -> 409）
   │  ├─ messaging/       # EventBus 实现：Redis Streams / Kafka / 内存
   │  ├─ cache/ security/ http/   # Cache / PasswordHasher / HttpClient 的实现（Redis·内存、scrypt、httpx）
   │  ├─ resources.py     # 启动时打开、关闭时释放的进程级资源
   │  └─ migrations/      # Alembic（async）
   └─ presentation/
      ├─ endpoint/        # 路由：RequestDTO + 注入的 usecase -> ResponseDTO
      ├─ schema/          # RequestDTO / ResponseDTO（pydantic），与 application model 互转
      ├─ dependency/      # 依赖注入（FastAPI Depends）：resources -> service -> usecase
      ├─ exception.py     # Result / HiaokError -> HTTP 状态码
      ├─ middleware.py    # X-Operator / X-Request-Id
      └─ openapi.py       # Swagger 配置
```

依赖方向：`presentation → application → domain ← infrastructure`，各层都可以用 `hiaok_core`。

**hiaok-core** 是独立仓库 <https://github.com/solomanpan/hiaok-core>（facade 接口、异常、JSON / fp 工具、请求上下文），
通过 uv 的 Git 依赖按 tag 引入（见 `pyproject.toml [tool.uv.sources]`）。升级：改 tag 后执行 `uv lock --upgrade-package hiaok-core`；
两边同时开发时可临时改成 `hiaok-core = { path = "../hiaok-core", editable = true }`，提交前改回 tag。
这些规则写在 `tests/unit/test_architecture.py` 里，违反时测试失败。

## 一次请求怎么走（以注册用户为例）

```
POST /api/v1/orgs/{org}/users
  UserRegisterRequest.to_command(org)                       # schema: RequestDTO -> RegisterUser
  uc: RegisterUserDep                                       # dependency: register_user(users, tenants, roles, hasher)
  register_user(...)(cmd)                                   # usecase: 柯里化，最后一个参数是请求数据
    RawPassword.create → tenants.get(@slave) → roles.list_by_uuids(@slave) → hash
    → users.register(@master)                               # service: 打开主库事务
        cmd.to_domain(uuid, hash) → User.register(...)      # domain: 校验 + 记录事件
        repo.save → DAO.to_do（user / user_detail / user_role）
        commit → after_commit: 发布 EntityCreated, UserRegistered
    .map(UserModel.from_domain)
  unwrap(result, UserResponse.of)                           # Error -> 422/404/409/403
```

## 写主读从：`@master` / `@slave`

```python
class RoleService(CrudService[Role]):
    @slave                      # 读：从库，只读事务
    async def get(...): ...

    @master                     # 写：主库；Ok -> commit，Error/异常 -> rollback
    async def grant_permissions(...): ...
```

规则（`infrastructure/database/routing.py` 实现，已在真实主从上验证）：

| 场景 | 行为 |
|---|---|
| 最外层被装饰的调用 | 打开会话（主库或从库） |
| `@slave` 嵌套在 `@master` 内 | 加入主库会话：读到自己刚写的数据 |
| `@master` 嵌套在 `@slave` 内 | 抛出 `DataSourceRoutingError` |
| 返回 `Error(...)` | 只有根作用域决定：回滚，`after_commit` 不执行 |
| `@slave` 里写数据 | 驱动层只读，数据库直接拒绝（即使 `DB_SLAVE_URL` 未配置、主从是同一库） |
| 领域事件 | 只在根事务提交成功后发布 |

多聚合原子写放在编排服务里：`ProvisioningService.provision`（组织 + 详情 + 默认租户 + ORG_ADMIN + 默认配置）、`OnboardingService.onboard`（入职 + 开账号 + 关联），外层 `@master` 一个事务，内层服务的 `@master` 自动加入。

仓储/DAO 从不自己开会话；在被装饰方法之外调用仓储会抛 `NoActiveScopeError`。同一作用域内不要 `asyncio.gather` 多个仓储调用（共享一个 AsyncSession）。

## 依赖注入（presentation/dependency/）

全部是 FastAPI `Depends`，分三层：`resources.py`（app.state 上的进程级资源）→ `service.py`（仓储实现注入应用服务）→ `usecase.py`（服务注入用例）。端点只声明需要的用例：

```python
@router.post("")
async def register_user(org_uuid: str, body: UserRegisterRequest, uc: RegisterUserDep) -> UserResponse:
    return unwrap(await uc(body.to_command(org_uuid)), UserResponse.of)
```

标准 CRUD 用 `CrudUseCases` 一组注册（`crud_usecases(service, Model.from_domain)`），组合用例单独注册。

## 事件驱动

- 总线：`APP_BROKER=redis`（Streams + consumer group）| `kafka`（key = 聚合 id）| `memory`（进程内）
- 消费者（`application/usecase/event_handler.py`）：所有领域事件 → `sys_log` 审计；`SysConfigChanged` → 驱逐缓存
- 至少一次投递：`sys_log.log_uuid` 由 `event_id` 派生 + `ON CONFLICT DO NOTHING`，重放不会重复
- 部署：API 设 `APP_CONSUME_EVENTS=false` 只发布，`hiaok worker` 单独消费并可水平扩展

## 配置

`APP_ENV`（真实环境变量）选择 profile：读取 `.env` 再读 `.env.<APP_ENV>`，真实环境变量优先。前缀：`APP_` / `DB_` / `REDIS_` / `KAFKA_`，见 `.env.example`。

| profile | 总线/缓存 | 数据库 |
|---|---|---|
| `dev` | Redis | 主 5432 + 从 5433 |
| `test` | 内存 | 单库 `hiaok_test`（从库引擎仍只读） |
| `docker` | Redis（或 Kafka） | compose 内主从 |

## 运行

```bash
uv sync
docker compose up -d postgres-master postgres-slave redis   # 只起基础设施
uv run alembic upgrade head                                  # 迁移永远走主库
uv run hiaok                                                 # API  http://localhost:8000/docs
uv run hiaok worker                                          # 消费者（APP_CONSUME_EVENTS=false 时需要）

docker compose up -d --build                                 # 全部容器：主从 + redis + migrate + api + worker
docker compose --profile kafka up -d --build                 # 加 Kafka，并设 APP_BROKER=kafka
```

迁移：`uv run alembic revision --autogenerate -m "..."`（配置在 `pyproject.toml [tool.alembic]`；`-x url=...` 可指定库）。不使用触发器：`update_time` 由 SQLAlchemy `onupdate=func.now()` 在每条 UPDATE 中写入（PostgreSQL 本身不会自动刷新）。改表后执行 `uv run python scripts/gen_db_doc.py` 重新生成 [`db.properties.md`](db.properties.md)（全量建表 SQL，测试会校验它是否过期）。

## 新增一个聚合

1. `domain/entity/xxx.py`（`create` 返回 `Result`，记录事件）+ `domain/repository` 里加仓储接口
2. `infrastructure/do/xxx.py`（`XxxDO`）→ `alembic revision --autogenerate` → `scripts/gen_db_doc.py`
3. `infrastructure/dao`：`XxxDao(EntityDao[XxxDO, Xxx])` 实现 `to_entity` / `to_do`；单表聚合的仓储只需 `SqlRepository(db, XxxDao(db))`
4. `application/model/xxx.py`（`XxxModel`/`CreateXxx`/`UpdateXxx`）+ `application/service`（继承 `CrudService`）
5. `presentation/schema/xxx.py`（DTO）+ `presentation/dependency` 注册 + `presentation/endpoint/xxx.py` 路由

## 注意

- `user` 是 PostgreSQL 保留字。ORM 会自动加引号；手写 SQL 必须写 `"user"`（`SELECT * FROM user` 返回的是 current_user）。
- 从库有复制延迟：写完立刻 `GET` 可能短暂 404。写接口直接返回主库上的结果，客户端不需要回读。
- 事件在提交后发布，进程在两者之间崩溃会丢事件；需要严格保证时改为 transactional outbox。
- `X-Operator` 请求头写入 `opr`，只是占位；接入认证后替换为登录主体。
- `dependency-injector` 仍在依赖列表中但已不使用，可以移除。

## API 文档（Swagger）

启动后访问：Swagger UI `http://localhost:8000/docs` · ReDoc `/redoc` · OpenAPI `/openapi.json`。

- 按业务分组（tag）并附说明；operationId 形如 `role-create_role`，便于生成客户端
- 每个 `/api/v1` 接口都标注了 403/404/409 错误结构，以及 `X-Operator` / `X-Request-Id` 请求头（可在 Swagger 里直接填写）
- 生产环境如不对外，设置 `APP_DOCS_ENABLED=false` 关闭这三个地址

## 测试

```text
tests/
├─ conftest.py              # 共享 fixture：内存 EventBus / Cache
├─ unit/                    # 纯内存，无外部依赖，按 DDD 分层
│  ├─ domain/               # 值对象、聚合、树、授权规则
│  ├─ application/          # 事件处理用例（用 Fake 替代需要 DB 的 service）
│  ├─ infrastructure/       # serde、内存总线、重试、内存缓存
│  └─ presentation/         # Result -> HTTP 状态码映射
└─ integration/             # 需要真实服务，自动打 integration 标记，连不上就 skip
```

```bash
uv run pytest                    # 全部（集成测试在没起服务时自动跳过）
uv run pytest -m "not integration"
docker compose up -d redis && uv run pytest -m integration
```
