# hiaok — a lightweight permission center

**English** · [日本語](readme-jp.md) · [中文](readme-zh.md) · Architecture design document: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

Four DDD layers + event-driven design + write-to-master / read-from-slave. Python 3.12 · FastAPI · SQLAlchemy 2 (asyncpg) · Alembic · Expression · Redis (cache / Streams) · Kafka

It provides management APIs for organizations, tenants, users, user groups, projects, roles, permissions, menus, departments, employees, system configuration and audit logs, plus login authentication (bearer token + permission codes) and localized error messages (en / zh / ja).

This document is organized by topic:

1. [Quick start](#1-quick-start)
2. [How to use this DDD framework](#2-how-to-use-this-ddd-framework)
3. [How authorization works](#3-how-authorization-works)
4. [Using Kafka](#4-using-kafka)
5. [Using Redis](#5-using-redis)
6. [Internationalization (i18n)](#6-internationalization-i18n)
7. [API conventions](#7-api-conventions)
8. [Configuration reference](#8-configuration-reference)
9. [Testing and caveats](#9-testing-and-caveats)

---

## 1. Quick start

```bash
uv sync
docker compose up -d postgres-master postgres-slave redis   # infrastructure only
uv run alembic upgrade head                                  # migrations always go to the master
uv run hiaok                                                 # API  http://localhost:8000/docs
uv run hiaok worker                                          # event consumer (needed when APP_CONSUME_EVENTS=false)

docker compose up -d --build                                 # everything: master+slave, redis, migrate, api, worker
docker compose --profile kafka up -d --build                 # + Kafka (and set APP_BROKER=kafka)
```

- Configuration: the real environment variable `APP_ENV` selects a profile; `.env` is read first, then `.env.<APP_ENV>`; real environment variables win. See the [configuration reference](#8-configuration-reference).
- Migrations: `uv run alembic revision --autogenerate -m "..."`. No triggers are used: `update_time` is written by SQLAlchemy `onupdate=func.now()` on every UPDATE. After changing tables run `uv run python scripts/gen_db_doc.py` to regenerate [`db.properties.md`](db.properties.md) (a test checks it is up to date).
- A fresh system has no users. Start with `AUTH_ENABLED=false`, create the organization, roles and an administrator, then turn authentication on (see [how authorization works](#3-how-authorization-works)).

## 2. How to use this DDD framework

### 2.1 Layers and dependency direction

```
presentation → application → domain ← infrastructure          (every layer may use hiaok_core)
```

```
src/                              # the business package (src itself is the package): relative imports inside, `from src.domain ...` in tests / scripts
├─ main.py                        # CLI `hiaok` (API) | `hiaok worker` (consumer); create_app() / lifespan
├─ domain/                        # depends on hiaok_core only, no framework
│  ├─ entity/                     # entities and aggregate roots (create returns a Result and records domain events); event.py = all domain events
│  ├─ vo/  enum/                  # value objects (validated on construction), enums
│  ├─ service/                    # domain services: tree (build / cycle guard), authority (union of permissions)
│  └─ repository/                 # repository interfaces (Protocol) + Page / PageQuery
├─ application/
│  ├─ config/                     # app / auth / database / redis / kafka settings (pydantic-settings)
│  ├─ model/                      # application models: XxxModel(from_domain/to_domain), CreateXxx, UpdateXxx
│  ├─ service/                    # @master / @slave application services (transaction boundary)
│  └─ usecase/                    # curried usecases + event handlers + write-command handling
├─ infrastructure/
│  ├─ database/ do/ dao/ repository/   # master/slave engines, table objects XxxDO, DAOs (to_entity / to_do), repository implementations
│  ├─ messaging/                  # EventBus: Redis Streams / Kafka / in-memory; topics.py = Kafka routing
│  ├─ cache/ security/ http/      # Cache (Redis / memory), PasswordHasher (scrypt), HttpClient (httpx)
│  └─ resources.py  migrations/   # process-wide resources; Alembic
└─ presentation/
   ├─ endpoint/                   # routes: request DTO + injected usecase -> response DTO
   ├─ schema/                     # DTOs (pydantic, camelCase) <-> application models
   ├─ dependency/                 # dependency injection: resources -> service -> usecase; authorization guards
   └─ exception.py middleware.py i18n.py messages.py security.py openapi.py
```

**hiaok-core** is a separate repository, <https://github.com/solomanpan/hiaok-core> (facade interfaces, exceptions, JSON / fp helpers, request context), pulled in as a uv Git dependency pinned to a tag. To upgrade: change the tag in `pyproject.toml [tool.uv.sources]`, then run `uv lock --upgrade-package hiaok-core`. While developing both repositories, you may temporarily point it at a local `path` dependency; switch back to the tag before committing.

These rules live in `tests/unit/test_architecture.py` and fail the build when broken: layer dependency direction, the sub-packages each layer may contain, no `port / PO / mapper` naming, data objects are named `XxxDO`, every DAO has `to_entity / to_do`, business errors must come from error catalogs, relative imports inside `src`.

### 2.2 Life of a request (registering a user)

```
POST /v1/api/hiaok/user/add   {"requestId": "...", "reqInfo": {"orgUuid": "...", ...}}
  ApiRequest[UserRegisterRequest].req_info.to_command()     # schema: request DTO -> RegisterUser
  usecase: RegisterUserDep                                  # dependency: register_user(users, tenants, roles, hasher)
  register_user(...)(cmd)                                   # usecase: curried, the request data is the last argument
    RawPassword.create → tenants.get(@slave) → roles.list_by_uuids(@slave) → hash
    → users.register(@master)                               # service: opens a master transaction
        cmd.to_domain(uuid, hash) → User.register(...)      # domain: validation + records events
        repo.save → DAO.to_do (user / user_detail / user_role)
        commit → after_commit: publish EntityCreated, UserRegistered
    .map(UserModel.from_domain)
  reply(result, UserResponse.of)                            # -> {"code": 0, "msg": "success", "resultInfo": {...}}
                                                            #    Error -> {"code": 400/403/404/409, "msg": ..., "errorCode": ...}
```

### 2.3 Adding an aggregate (`Xxx`)

1. **Domain**: `domain/entity/xxx.py` — `create(...)` returns `Result[Xxx, DomainError]` and records events; business errors go into an `XxxErrors(ErrorCatalog)` in the same file; add the repository interface under `domain/repository`.
2. **Table**: `infrastructure/do/xxx.py` (`XxxDO`) → `alembic revision --autogenerate` → `scripts/gen_db_doc.py`.
3. **DAO / repository**: `XxxDao(EntityDao[XxxDO, Xxx])` implements `to_entity` / `to_do`; a single-table aggregate's repository is just `SqlRepository(db, XxxDao(db))`.
4. **Application**: `application/model/xxx.py` (`XxxModel` / `CreateXxx` / `UpdateXxx`) + `application/service` (extend `CrudService`; `@master` for writes, `@slave` for reads).
5. **Presentation**: `presentation/schema/xxx.py` (DTOs) + register the service and usecases in `presentation/dependency` + routes in `presentation/endpoint/xxx.py`.
6. **Register the write handlers**: add a handler in `build_write_handlers` (`presentation/dependency/command.py`; standard CRUD is a one-liner `_crud(...)`). `test_write_handlers.py` checks that endpoints and handlers match one to one.
7. **Kafka routing**: give the new entity and its events a topic in `infrastructure/messaging/topics.py` (the tests fail if you forget).
8. **Authorization and translations**: add `dependencies=[has_permission("xxx:add")]` to the routes; add the error messages to `presentation/messages.py` (the tests fail on missing translations).

You can also generate this skeleton from the meta templates (jinja2) in `codegen/` and a spec file; see [codegen/README.md](codegen/README.md).

### 2.4 Writing each layer

**Endpoints**: the request and response types sit in the function signature; FastAPI validates with them and generates Swagger. Every endpoint is a `POST` and success is expressed by `code`, so no `status_code` is needed.

```python
@router.post("/add", dependencies=[has_permission("role:add")])
async def create_role(
    request: ApiRequest[RoleCreateRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(await submitter.create("Role", request.request_id, info.org_uuid, info.to_command()))
```

**Dependency injection** (`presentation/dependency/`): everything is FastAPI `Depends`, in three tiers: `resources.py` (process-wide resources on `app.state`) → `service.py` (repository implementations injected into application services) → `usecase.py` (services injected into usecases). An endpoint only declares the usecase it needs, e.g. `usecase: RegisterUserDep`. Standard CRUD is registered as a group with `crud_usecases(service, Model.from_domain)`; composite usecases are registered one by one.

**Usecases**: curried functions — dependencies first, request data last — composed with `AsyncResult` chains (`bind / map / ensure`). They return a `Result` and do not raise business exceptions.

**Error catalogs**: declare each business error once (kind + code + message template); never assemble `conflict(...)` ad hoc:

```python
class RoleErrors(ErrorCatalog):
    system_role = ErrorSpec.conflict("system_role", "system role '{code}' cannot be deleted")


return RoleErrors.system_role.err(code=self.role_code)  # Result style
RoleErrors.system_role.raise_(code=...)  # when an exception is unavoidable
```

Rules that span aggregates live in `application/usecase/errors.py` (`UseCaseErrors`); the generic `not_found(entity, id)` is used directly.

**Write to master, read from slave**:

```python
class RoleService(CrudService[Role]):
    @slave                      # read: slave, read-only transaction
    async def get(...): ...

    @master                     # write: master; Ok -> commit, Error/exception -> rollback
    async def grant_permissions(...): ...
```

| Situation | Behavior |
|---|---|
| Outermost decorated call | opens the session (master or slave) |
| `@slave` nested inside `@master` | joins the master session: reads its own writes |
| `@master` nested inside `@slave` | raises `DataSourceRoutingError` |
| Returns `Error(...)` | only the root scope decides: rollback, `after_commit` does not run |
| Writing inside `@slave` | the driver is read-only; the database rejects it |
| Domain events | published only after the root transaction commits |

Atomic multi-aggregate writes live in orchestration services: `ProvisioningService.provision` (organization + detail + default tenant + ORG_ADMIN + default configuration) and `OnboardingService.onboard` (hire + open account + link). The outer `@master` is one transaction; inner `@master` services join it. Repositories / DAOs never open sessions themselves — calling them outside a decorated method raises `NoActiveScopeError`; never `asyncio.gather` several repository calls in one scope (they share one AsyncSession).

**Test data**: `tests/factories.py` (polyfactory): `RoleFactory.build(...)`, `PermissionFactory.batch(3)`. Factories construct entities directly (no validation, no events); use the aggregate's `create` / `register` when validation or events are what you test.

## 3. How authorization works

### 3.1 Flow

```
POST /auth/login {orgUuid, tenantUuid, username, password}
  → check the user (enabled), the password (scrypt) and the tenant (enabled, not expired)
  → create a random token; the session {userUuid, orgUuid, tenantUuid} is stored in the cache (TTL = AUTH_SESSION_TTL_SECONDS, default 2 h)
  ← accessToken

every later request: Authorization: Bearer <token>
  middleware  token → session → fills the request context (operator = user uuid, org, tenant); the audit column opr is therefore the logged-in user
  guard       has_permission("role:add") / has_role("admin") / authenticated()
              session → authorities (user → enabled roles → permission codes; cached per user) → decision → pass / 401 / 403
```

The token is a random string that carries no information; only its SHA-256 is kept in the cache. `/auth/logout` deletes the session, which revokes the token at once.

### 3.2 Declaring it on an endpoint

```python
@router.post(
    "/add", dependencies=[has_permission("role:add")]
)  # any of the codes; role:* covers role:add, * covers everything
@router.post("/list", dependencies=[has_role("admin", "auditor")])  # any of the roles
@router.post("/me", dependencies=[authenticated()])  # any logged-in user
async def handler(principal: PrincipalDep): ...  # when you need to know who is calling
```

- **Permission-code convention**: `<resource>:<action>`, e.g. `role:grant-permissions`, `menu:move`; actions match routes one to one. Which role holds which code is data in the permission tables, so changing grants needs no code change. Prefer `has_permission`; keep `has_role` for a few cases such as "super administrator".
- **Tenant isolation**: when `reqInfo.orgUuid` in the body is not the caller's organization the guard answers 403 `org_mismatch`. The platform organization named by `AUTH_PLATFORM_ORG_UUID`, and users holding `*`, may cross organizations.
- **Results**: not logged in / token invalid or expired → `code` 401 (`unauthenticated`); missing permission → 403 (`permission_denied` / `role_denied`). The HTTP status stays 200, like every other business error.
- **Switch**: with `AUTH_ENABLED=false` every guard lets the call through and the `X-Operator` header names the operator (local debugging, first-time setup).

### 3.3 How permissions and menus are computed

Permissions = user → enabled roles → union of permission codes. Menus = the same roles → union of menus, keeping only enabled and visible ones, assembled into a tree (`domain/service/authority.py`).

- `/auth/me` returns `roleCodes`, `permissionCodes` and the menu tree; the front end calls it once after login to render the sidebar. **Menus only decide what the front end shows; whether an API call is allowed is always decided by that endpoint's own guard.**
- Role and permission codes are cached per user for `AUTH_AUTHORITY_TTL_SECONDS` (default 60 s). Create / update / delete events of users, user groups, roles and permissions, plus role-grant / menu-assignment events, invalidate the whole organization's cache at once (see [Using Redis](#5-using-redis)). The menu tree is not cached: `/auth/me` queries the database each time.

### 3.4 Current state and to-do

- Today `role`, `menu` and `/auth/*` use guards; other resources do not yet. `UNGUARDED_YET` in `tests/unit/presentation/test_security.py` lists the resources still open, and a new endpoint without a guard fails the test. When a resource is fully guarded, remove it from that set.
- `/user/authorities` has no guard yet — anyone can query anyone's authorities. Add one soon.
- The first administrator is created by hand (start with `AUTH_ENABLED=false` and register).

## 4. Using Kafka

### 4.1 When it is used

With `APP_BROKER=kafka`, Kafka is the **event bus** and carries two kinds of messages:

1. **Write commands** (`WriteRequested`): the endpoint only publishes, a consumer executes (see 4.5).
2. **Domain events** (`EntityCreated`, `UserRegistered`, `RolePermissionsChanged`, …): published after the transaction commits; consumers write the audit log and evict caches.

For development and tests use `APP_BROKER=memory` (in-process; write requests run synchronously inside `publish`, no external service). For small deployments the default Redis Streams works (section 5).

### 4.2 Topic design

Five topics by business domain; a write command and the domain events it causes use the same topic:

| Topic (default prefix `hiaok`) | Entities | Dead-letter topic |
|---|---|---|
| `hiaok.organization` | organization, tenant, project | `hiaok.organization.dlq` |
| `hiaok.identity` | user, user group | `hiaok.identity.dlq` |
| `hiaok.authorization` | role, permission, menu | `hiaok.authorization.dlq` |
| `hiaok.hr` | employee, department | `hiaok.hr.dlq` |
| `hiaok.config` | system configuration | `hiaok.config.dlq` |

- The routing table is in `infrastructure/messaging/topics.py` (`Topic`, `TOPIC_OF_ENTITY`, `TOPIC_OF_EVENT`, `topic_of`). A new entity or event without a route raises `UnroutableEvent`, and the tests fail.
- **Message key = aggregate id** (the target uuid for write commands): messages of one aggregate land in one partition, which keeps their order.
- **Payload**: JSON `{"event_type": "...", "payload": {...}}`; the `event_type` header is set. An unknown `event_type` (an event from a newer release) is skipped.

### 4.3 Producing

The producer uses `acks=all` and `enable_idempotence=True`, with `send_and_wait` (returns once the broker has the message).

```python
# the endpoint needs just this line; the bus does the rest
await submitter.update("Role", request.request_id, org_uuid, uuid, command)
#  → WriteRequested(entity_type="Role", command_type="Role.update", target_uuid=uuid, payload=...)
#  → topic_of(event) = hiaok.authorization, key = uuid
```

### 4.4 Consuming

One consumer per topic, group = `<KAFKA_GROUP_ID>.<topic>` (e.g. `hiaok.authorization`), `auto_offset_reset=earliest`, **manual offset commit**:

```
fetch → deserialize → find subscribers → run (on failure retry 3 times, 0.2 s / 0.4 s / 0.6 s apart)
   ├─ success (or unknown event) → commit the offset
   └─ still failing (or undecodable) → copy as-is to <topic>.dlq with headers source_topic / source_partition / source_offset → commit the offset
```

An offset is committed only after the message was handled or dead-lettered, so nothing is lost, and one poison message never blocks a topic. Delivery is **at least once**: consumers must be idempotent (write commands de-duplicate through the outcome record derived from `requestId`, see 4.5).

Consumers of domain events (`application/usecase/event_handler.py`):

| Event | Handling |
|---|---|
| every domain event (except `WriteRequested`) | write an audit row to `sys_log`; `log_uuid` is derived from `event_id`, so replays are safe |
| `SysConfigChanged` | evict the configuration cache |
| create / update / delete of users, user groups, roles, permissions; role grants, menu assignment, user role assignment | invalidate that organization's authority cache |

### 4.5 The full asynchronous write flow

`add / update / delete` and the special write actions (grant, move, onboard / resign / transfer, …) do not write to the database directly:

```
POST /v1/api/hiaok/role/update          {requestId, reqInfo}
  endpoint:  WriteSubmitter.update("Role", ...) → publishes WriteRequested (key = target uuid) → returns at once
             {"code": 0, "resultInfo": {"requestId": "...", "uuid": "...", "status": "accepted"}}
  consumer:  handle_write → handlers["Role.update"] → the original usecase → service(@master) → database
             success: an outcome record is written in the same transaction (sys_log, log_type=command)
             business failure (duplicate code, role not found, …): rollback and record the failure, no retry
             exception (database down, …): re-raised, the bus retries 3 times, then dead-letters
  look up:   POST /v1/api/hiaok/log/get-by-request  {orgUuid, targetRequestId}
             → status = success | failed | pending (code / msg / errorCode as the synchronous call would give; msg follows Accept-Language)
```

- The **uuid of a new entity** is derived from `requestId` (`application/service/ids.py`), so the endpoint can return it before the entity exists; the consumer generates ids from the same sequence, so a redelivery creates the same ids.
- **Idempotency**: the outcome record's `log_uuid` is derived from `requestId`; if it exists the message is skipped. The outcome record and the business write share one transaction — both commit or both roll back. Submitting the same `requestId` again runs only once.
- `pending` means: not consumed yet, being retried, or dead-lettered. A dead-lettered command needs manual handling (see 4.7).
- **Endpoints that stay synchronous**: user registration (`/user/add`), change password, employee onboarding (`/employee/add`, optionally with an account). They carry a clear-text password, which must never be written to Kafka (messages are persisted).
- A new write endpoint = register its handler in `build_write_handlers`.

### 4.6 Configuration

| Variable | Default | Meaning |
|---|---|---|
| `APP_BROKER` | `redis` | `redis` \| `kafka` \| `memory` |
| `APP_CONSUME_EVENTS` | `true` | `false`: this process only publishes; run `hiaok worker` to consume, scale it horizontally |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9094` | inside containers use `kafka:9092` |
| `KAFKA_TOPIC_PREFIX` | `hiaok` | topic = `<prefix>.<domain>` |
| `KAFKA_GROUP_ID` | `hiaok` | consumer group = `<group_id>.<domain>` |
| `KAFKA_DLQ_SUFFIX` | `.dlq` | dead-letter topic suffix |
| `KAFKA_CREATE_TOPICS` | `true` | create the 10 topics (5 domain + 5 dead-letter) at startup, ignore existing; in production turn it off and let operations create them |
| `KAFKA_NUM_PARTITIONS` | `3` | partitions when creating topics |
| `KAFKA_REPLICATION_FACTOR` | `1` | replicas when creating topics; set according to the number of brokers in production |

Deployment shapes:

```
          ┌─ api (APP_CONSUME_EVENTS=false) ──publish──▶ Kafka ◀──consume── worker × N (hiaok worker)
 client ──┤
          └─ or a single process: the api also consumes (APP_CONSUME_EVENTS=true, the default)
```

The more workers in one group, the more evenly partitions are shared; parallelism is capped by the partition count.

### 4.7 Operations

- **Inspect dead letters**: consume `hiaok.<domain>.dlq`; the headers `source_topic / source_partition / source_offset` point at the original message. The body equals the original, so after fixing the cause publish it back to the original topic (consumption is idempotent).
- **Check a write request**: `/log/get-by-request`; when it is `pending`, look at the consumer logs, then at the matching `.dlq`.
- **Add a topic**: ① add a member to the `Topic` enum; ② map the entity in `TOPIC_OF_ENTITY` (and events in `TOPIC_OF_EVENT` if there are any); ③ register write handlers in `build_write_handlers`; ④ add a routing case to `test_topics.py`; ⑤ in production create the topic and its `.dlq` first. Consumers and groups are generated from the enum, so the bus code does not change.
- Trying Kafka locally: `docker compose --profile kafka up -d --build` and set `APP_BROKER=kafka`; the integration tests skip themselves when Kafka is unreachable.

## 5. Using Redis

Redis has two independent uses, switched separately:

| Use | Switch | Notes |
|---|---|---|
| Event bus (Streams) | `APP_BROKER=redis` (default) | alternative to Kafka |
| Cache | `APP_CACHE=redis` (default) | `APP_CACHE=memory` uses an in-process cache (single node / tests; not shared between replicas) |

### 5.1 Cache

Every key is prefixed with `REDIS_CACHE_PREFIX` (default `hiaok:`) and has the default TTL `REDIS_CACHE_TTL_SECONDS` (300 s). The interface is just `get / set(ttl) / delete`, defined by `hiaok_core.facade.Cache`.

| Key (without prefix) | Content | TTL | Invalidation |
|---|---|---|---|
| `sys_config:<org>:<key>` | system configuration (read-through, `SysConfigService.get_by_key`) | 300 s | the `SysConfigChanged` event evicts it after any committed write |
| `session:<sha256(token)>` | login session `{userUuid, orgUuid, tenantUuid}` | `AUTH_SESSION_TTL_SECONDS` (2 h) | deleted on logout; expires by itself |
| `authz:<org>:<version>:<user>` | the user's role codes + permission codes | `AUTH_AUTHORITY_TTL_SECONDS` (60 s) | see below |
| `authz_ver:<org>` | the organization's authority-cache version | 1 day | set to a new value when relevant events arrive |

**How a whole group is invalidated**: the key contains the organization's version. When a change event of users, user groups, roles or permissions arrives, only `authz_ver:<org>` is rewritten; the old keys of every user in that organization stop being found at once (and expire naturally) — no scanning or deleting is needed.

### 5.2 Event bus (Redis Streams)

With `APP_BROKER=redis`, `infrastructure/messaging/redis_stream.py`:

| Aspect | Implementation |
|---|---|
| Publish | `XADD hiaok-events * data <json>`, `MAXLEN ~ 100000` (approximate trimming) |
| Consume | consumer group `hiaok`, consumer `consumer-1`, `XREADGROUP ... >`, up to 50 messages per call, blocking 1 s |
| Group creation | `XGROUP CREATE ... $ MKSTREAM` at startup, ignored if it exists; **only messages after the group was created are consumed** |
| Acknowledge | `XACK` only after success (or an unknown event) |
| Retry | 3 in-process attempts (0.2 s / 0.4 s / 0.6 s) |
| Failure | no `XACK`; the message stays in the PEL (pending entries list) |

Differences from Kafka (worth knowing when you choose):

- There is **one stream and one consumer group**, not split by domain, and **no dead-letter queue**. A failed message stays in the PEL; inspect it with `XPENDING hiaok-events hiaok`, re-claim it with `XAUTOCLAIM`, or move it by hand.
- With several consumers in a group, messages are shared among them. The consumer name defaults to a fixed `consumer-1`; with several worker replicas give each its own `REDIS_CONSUMER_NAME`.
- There is no key partitioning, so **per-aggregate ordering is not guaranteed** when several consumers run in parallel. Choose Kafka when you need strict ordering, higher throughput or longer retention.
- The write-command flow, idempotency and outcome lookup are exactly the same as with Kafka.

### 5.3 Configuration

| Variable | Default | Meaning |
|---|---|---|
| `REDIS_URL` | `redis://localhost:6379/0` | shared by cache and Streams |
| `REDIS_STREAM` | `hiaok-events` | stream name |
| `REDIS_CONSUMER_GROUP` | `hiaok` | consumer group |
| `REDIS_CONSUMER_NAME` | `consumer-1` | set a different value per replica |
| `REDIS_STREAM_MAXLEN` | `100000` | approximate maximum length |
| `REDIS_CACHE_PREFIX` | `hiaok:` | cache key prefix (the stream is not prefixed) |
| `REDIS_CACHE_TTL_SECONDS` | `300` | default cache TTL |

## 6. Internationalization (i18n)

Error messages come back in the caller's language: `Accept-Language: zh-CN,zh;q=0.9,en;q=0.8` → the supported language (`en` / `zh` / `ja`) with the highest `q`; the response carries `Content-Language`. If none is supported, `APP_DEFAULT_LOCALE` (default `en`) is used.

- **Codes never change**: `code` and `errorCode` are always the same; only `msg` is translated. Clients should branch on `errorCode` and use `msg` for display only.
- **How it works**: a business error is a value built from an English template in a catalog plus parameters. For display, the message is matched back to its error spec (both code and text must match), the parameters are read out, and they are poured into the translated template in `presentation/messages.py`; words such as `entity` (`User` → `用户`) are translated too. A message without a translation stays English.
- **Adding an error message**: after declaring it in the catalog, add `zh` and `ja` entries to `TEMPLATES` in `presentation/messages.py` (the key is the English template). `tests/unit/presentation/test_i18n.py` fails on a missing translation, on mismatching placeholders, and on a translation whose message no longer exists.
- **Adding a language**: add the code to `LOCALES` and the language to every entry of `messages.py`; the test lists what is missing.
- **Scope**: `msg` of API responses (including failure results of asynchronous writes) and the fixed 401 / 500 texts. Request-body format messages come from pydantic and are not translated; the Swagger descriptions stay Chinese.

## 7. API conventions

Every endpoint is `POST /v1/api/hiaok/<resource>/<action>`, the request is `{requestId, reqInfo}`, the response is `{code, msg, resultInfo}`, fields are camelCase; the organization is `reqInfo.orgUuid`, the target resource is `reqInfo.uuid`.

| Header | Meaning |
|---|---|
| `Authorization: Bearer <token>` | required by protected endpoints (obtain it from `POST /auth/login`) |
| `Accept-Language` | `en` / `zh` / `ja`, the language of `msg` |
| `X-Request-Id` | trace id, echoed in the response header; generated if absent |
| `X-Operator` | only used when `AUTH_ENABLED=false` |

Expected errors are HTTP 200 with a `code`:

| code | Meaning |
|---|---|
| 0 | success |
| 400 | business validation failed, or malformed request body (`errorCode` = `invalid_request`) |
| 401 | not logged in / token invalid (`unauthenticated`), or wrong username or password (`invalid_credentials`) |
| 403 | no permission (`permission_denied` / `role_denied`), or acting on another organization (`org_mismatch`) |
| 404 | resource not found |
| 409 | state conflict (duplicate code, deleting a system role, …) |
| 502 / 500 | upstream failure / unexpected system error (these two are real HTTP statuses; details go to the log only) |

List endpoints take `offset` (default 0) and `limit` (default 20, max 200) in `reqInfo`; `resultInfo` is `items / total / offset / limit`.

Swagger: `http://localhost:8000/docs` · ReDoc `/redoc` · `/openapi.json`. Protected endpoints declare the bearer scheme; paste the token into Authorize at the top right to try them. If the docs must not be public set `APP_DOCS_ENABLED=false`.

## 8. Configuration reference

`APP_ENV` selects the profile (`dev`: Redis + master 5432 / slave 5433; `test`: memory + a single database; `docker`: master/slave inside compose).

| Prefix | Variable | Default |
|---|---|---|
| `APP_` | `NAME` `ENV` `HOST` `PORT` `LOG_LEVEL` | `hiaok` / `dev` / `0.0.0.0` / `8000` / `INFO` |
| | `BROKER` | `redis` (`kafka` \| `memory`) |
| | `CACHE` | `redis` (`memory`) |
| | `CONSUME_EVENTS` | `true` |
| | `DOCS_ENABLED` | `true` |
| | `DEFAULT_LOCALE` | `en` (`zh` \| `ja`) |
| `AUTH_` | `ENABLED` | `true` |
| | `SESSION_TTL_SECONDS` | `7200` |
| | `AUTHORITY_TTL_SECONDS` | `60` (1–86400) |
| | `PLATFORM_ORG_UUID` | empty |
| `DB_` | `MASTER_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/hiaok` |
| | `SLAVE_URL` | empty (reads go to the master too) |
| | `POOL_SIZE` `MAX_OVERFLOW` `POOL_RECYCLE` `ECHO` | `10` / `20` / `1800` / `false` |
| `REDIS_` / `KAFKA_` | see sections 4 and 5 | |

## 9. Testing and caveats

```bash
uv run pytest                          # everything (integration tests skip themselves when services are down)
uv run pytest -m "not integration"
docker compose up -d redis && uv run pytest -m integration
uv run ruff check . && uv run ruff format --check . && uv run pyright
```

```text
tests/
├─ unit/domain/          # value objects, aggregates, tree, authorization rules
├─ unit/application/     # write commands (idempotency, failure records), event handling
├─ unit/infrastructure/  # serde, in-memory bus, topic routing, cache, DAO conversion
├─ unit/presentation/    # envelope, exception mapping, authorization guards, i18n, OpenAPI
├─ unit/test_architecture.py    # layering and naming rules
└─ integration/          # need real Redis / Kafka; skipped when unreachable
```

- `user` is a reserved word in PostgreSQL. The ORM quotes it automatically; hand-written SQL must write `"user"`.
- The slave lags behind the master: a read right after a write may briefly miss it. With asynchronous writes, confirm through `/log/get-by-request` instead of reading back immediately.
- Events are published after commit; a crash between the two loses the event. Switch to a transactional outbox when you need a strict guarantee.
- A write command that was dead-lettered shows `pending` forever and needs manual handling.

## License

[MIT](LICENSE) © 2026 PAN JIE <sanbaikuai@gmail.com>
