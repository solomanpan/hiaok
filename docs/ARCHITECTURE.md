# hiaok — System Architecture and Design Rationale

This document explains **how the system is built and why**. For how to run it and how to add things to it, see the
[English guide](../readme-en.md).

## 1. Goals, scope, non-goals

hiaok is a **lightweight permission center**: it manages organizations, tenants, users, user groups, projects, roles,
permissions, menus, departments, employees and system configuration, authenticates callers, and answers "what may this
user do / see".

Design goals, in priority order:

1. **Correctness of authorization data** — role / permission / menu changes are transactional and auditable.
2. **A codebase that stays uniform** — dozens of resources follow one shape, so they can be generated and reviewed
   quickly; the rules are enforced by tests, not by convention.
3. **Operable with few moving parts** — PostgreSQL + Redis is enough; Kafka is optional.
4. **Replaceable infrastructure** — the domain knows nothing about FastAPI, SQLAlchemy, Redis or Kafka.

Non-goals: a full IAM product (no SSO / OAuth server, no policy language such as ABAC), high-volume write throughput
(permission administration is low-volume), multi-region replication.

## 2. System context

```
                 ┌──────────────┐  HTTPS (POST, JSON envelope)   ┌────────────────────────────────┐
 Admin UI /      │   clients    │ ─────────────────────────────▶ │  api  (FastAPI, `hiaok`)       │
 other services  └──────────────┘ ◀───────────────────────────── │                                │
                                                                 └───────┬───────────┬────────────┘
                                                      publish events     │ read      │ write
                                                                         ▼           ▼
                                         ┌──────────────────┐   ┌───────────┐   ┌───────────┐
                                         │ Kafka / Redis    │   │ PostgreSQL│   │ PostgreSQL│
                                         │ Streams          │   │  slave    │◀──│  master   │ streaming
                                         └───────┬──────────┘   └───────────┘   └───────────┘ replication
                                                 │ consume                              ▲
                                                 ▼                                      │ write
                                         ┌──────────────────┐ ────────────────────────────┘
                                         │ worker(s)        │      cache / sessions
                                         │ (`hiaok worker`) │ ──────────────────────────▶ Redis
                                         └──────────────────┘
```

The API and the worker are the same code base (`hiaok` / `hiaok worker`). With `APP_CONSUME_EVENTS=true` one process
does both; in production they are usually split so consumers scale independently.

## 3. Layered architecture

```
presentation  →  application  →  domain  ←  infrastructure         (all may use hiaok_core)
 HTTP, DTOs,      use cases,       entities, value objects,          DB, cache, bus,
 DI, guards       services,        events, domain services,          password hashing,
                  transactions     repository interfaces             HTTP client
```

| Layer | Responsibility | Must not |
|---|---|---|
| `domain` | Business rules: entities, aggregates, value objects, domain events, domain services, repository *interfaces* | import any framework, ORM, or other layer |
| `application` | Orchestration: use cases (what a request does), application services (transaction boundary), models, configuration | import `infrastructure`, `presentation`, FastAPI, SQLAlchemy |
| `infrastructure` | Adapters: SQL (DO / DAO / repository), cache, event bus, hasher, HTTP client, migrations | import `presentation`, FastAPI |
| `presentation` | HTTP: routes, DTOs, dependency injection, authorization guards, error → envelope mapping, i18n | contain business rules |

**Why these rules are tests.** `tests/unit/test_architecture.py` parses imports and directory layout. A rule that
lives only in a document erodes within months; a failing test does not. The same file bans `port / PO / mapper`
naming, requires every DAO to implement `to_entity` and `to_do`, and requires business errors to come from error
catalogs.

**`hiaok-core`** is a separate repository holding what any service of this family needs: facade protocols (`Cache`,
`EventBus`, `TransactionManager`, `PasswordHasher`, `IdGenerator`, `HttpClient`), the error types, JSON and functional
helpers, and the request context. Application code depends on the *protocols*; `infrastructure/resources.py` is the
single place that wires concrete adapters (a composition root).

## 4. Domain model

### 4.1 Aggregates and tables

```
Organization ─┬─ OrgDetail
              ├─ Tenant ──┬─ User ─┬─ UserDetail
              │           │        └─ user_role (RoleAssignment: role × optional project)
              │           ├─ UserGroup (tree)
              │           └─ Role ─┬─ role_permission ── Permission
              │                    └─ role_menu ─────── Menu (tree)
              ├─ Project
              ├─ Department (tree) ── Employee ── (optional link to User)
              ├─ SysConfig
              └─ SysLog (audit + command outcomes)
```

Every row carries the organization (`org_uuid`) — organization is the top-level isolation key — plus audit columns
(`opr`, `create_time`, `update_time`, `delete_flag`). Deletion is soft.

### 4.2 Entities, value objects, events

- **Entities are immutable dataclasses.** Behavior returns a *new* entity and records events on it; nothing mutates in
  place. This keeps domain code pure and makes tests trivial.
- **Value objects validate on construction** (`Username`, `Email`, `PhoneNumber`, `Code`, `RawPassword`,
  `PasswordHash`). An invalid value cannot exist, so downstream code never re-validates. `RawPassword` has a masked
  `repr`, so it cannot leak into logs.
- **Domain events** are immutable facts (`UserRegistered`, `RolePermissionsChanged`, generic `EntityCreated /
  Updated / Deleted`). They subclass one base that registers itself by class name, which is how a message from a broker
  is turned back into a typed event.
- **Domain services** hold rules that belong to no single entity: `tree` (build a tree, prevent cycles) and
  `authority` (permissions = union over *enabled* roles; `role:*` and `*` wildcards).

### 4.3 Errors are values

Business failures are returned as `Result[T, DomainError]` (the Expression library), not raised. Reasons:

- The failure path is visible in the type, so callers cannot forget it.
- Chains (`AsyncResult.bind / map / ensure`) read as a pipeline; no try/except pyramid.
- A transaction decides commit-or-rollback from the *value* (`Ok` / `Error`) without exception semantics.

Exceptions remain for the unexpected (infrastructure down, programming errors). A `DomainError` is
`(kind, code, message)` with kind ∈ {validation, not_found, conflict, forbidden}.

**Error catalogs.** Every business error is declared once — kind, stable `code`, message template with
`{placeholders}` — in an `ErrorCatalog` next to the code that raises it. Benefits: codes are stable identifiers
clients can rely on; messages live in one place (so they can be translated, see §11); the catalog can be listed to
publish an error table; an architecture test rejects ad-hoc `conflict(...)` calls.

## 5. Persistence and read/write routing

### 5.1 DO / DAO / repository

```
Entity ──(DAO.to_do)──▶ XxxDO (SQLAlchemy row) ──▶ table
Entity ◀─(DAO.to_entity)── XxxDO
Repository (domain interface) ◀── SqlRepository (assembles an aggregate from several DAOs)
```

- **DO** (data object) = the ORM row. It is not the entity, so persistence concerns (column types, relationships) never
  leak into the domain.
- **DAO** = table-level access plus the two conversions. `LinkDao` diffs association tables (e.g. `role_permission`):
  removed links are soft-deleted, new ones inserted.
- **Repository** implements the domain interface, saving an aggregate inside a **SAVEPOINT** so a unique-constraint
  violation becomes a clean `Error(conflict)` without poisoning the outer transaction.

### 5.2 `@master` / `@slave`

Writes go to the master, reads to a replica. The decorator sits on **application service methods**, which makes the
service the transaction boundary.

```
@master  outermost  → open a master session; Ok → commit; Error / exception → rollback
@slave   outermost  → open a replica session, read-only transaction
nested   @slave in @master → joins the master session (read-your-writes)
         @master in @slave → DataSourceRoutingError (a write cannot hide inside a read)
```

Design points:

- **Only the root scope commits or rolls back.** Inner services join, so an orchestration service
  (`ProvisioningService.provision`, `OnboardingService.onboard`) composes several aggregate writes in **one atomic
  transaction** simply by being `@master` itself.
- **Repositories never open sessions.** They use the active scope; calling one outside a decorated method raises
  `NoActiveScopeError`. This prevents accidental autocommit writes and makes transaction boundaries auditable by eye.
- **The replica is enforced read-only at the driver**, so even with no replica configured (both URLs equal) a write
  inside `@slave` is rejected by the database.
- **Events are published only after the root commit.** A rollback therefore never emits events for state that does not
  exist. (The remaining gap — crash between commit and publish — is discussed in §14.)
- Replication lag is real: a read right after a write on a replica may miss it. Within a `@master` scope reads are
  consistent because they use the master session.

## 6. API design

```
POST /v1/api/hiaok/<resource>/<action>
{ "requestId": "...", "reqInfo": { "orgUuid": "...", "uuid": "...", ... } }
→ { "code": 0, "msg": "...", "resultInfo": { ... }, "errorCode": "..." }   (errorCode only on errors)
```

- **One envelope, always POST.** Parameters, including the target resource, live in the body, so URLs are stable
  identifiers of operations (good for gateways, permission codes and audit) and no resource ids leak into access logs.
- **`requestId` is mandatory.** It is the idempotency key of asynchronous writes (§7) and the correlation id in logs.
- **Business outcomes are HTTP 200 with `code`.** The transport worked; the business operation did not. Only real
  infrastructure problems use HTTP 5xx (502 upstream, 500 unexpected). The trade-off — HTTP-level monitoring cannot see
  business errors — is accepted; monitor by `code`.
- **camelCase on the wire, snake_case in Python**, generated by one alias function on the DTO base class.
- DTOs (`presentation/schema`) are separate from application models (`application/model`) and domain entities, so each
  layer can evolve its shape independently; `to_command()` / `XxxResponse.of()` are the only crossings.

Dependency injection is FastAPI `Depends` in three tiers — `resources → service → usecase` — and an endpoint declares only
the use case it needs. Use cases are **curried functions** (`register_user(users, tenants, roles, hasher)(cmd)`):
partial application at the DI edge gives a testable function with no class boilerplate.

## 7. Asynchronous writes (command / outcome)

### 7.1 Why

Writes (create / update / delete and special actions) are accepted by the API and executed by a consumer. This buys:
a uniform, ordered write path (per-aggregate ordering through the message key), back-pressure isolation between API
and database, and one place (the outcome record) that tells the caller what happened. It costs: eventual consistency
and operational complexity. For a low-volume permission center this is a deliberate trade-off, and §14 lists the
alternative (synchronous writes with an outbox) honestly.

### 7.2 Flow

```
API                                         broker                      consumer
 │  WriteSubmitter.update("Role", requestId, …)
 │  ── WriteRequested{requestId, command_type="Role.update", target_uuid, operator, payload} ─▶
 │  ◀─ {code:0, resultInfo:{requestId, uuid, status:"accepted"}}                │
 │                                                                              ▼
 │                                              handle_write → handler["Role.update"]
 │                                              CommandService.execute  (@master, ONE transaction)
 │                                                 outcome row exists?  ── yes → skip (idempotent)
 │                                                 run the original use case under request_context(operator)
 │                                                 Ok    → write outcome row (success) → commit
 │                                                 Error → rollback, then record_failure (separate transaction)
 │                                                 exception → propagate → bus retries → DLQ
 │  POST /log/get-by-request {targetRequestId} ───────────────────────────────▶ sys_log lookup
 │  ◀─ status = success | failed | pending
```

### 7.3 Design decisions

- **Idempotency by construction.** The outcome row's id is derived from `requestId` (`uuid5`), and it is written in the
  *same transaction* as the business change. Redelivery finds the row and does nothing; a crash before commit leaves no
  row and no change, so retry is safe. Both commit or neither does.
- **Deterministic ids.** A new entity's uuid is derived from `requestId` plus a counter (a ContextVar `next_id()`
  replaces random ids while a command runs). Consequences: the API can return the new uuid *before* the entity exists;
  a redelivery re-creates the same ids instead of duplicates.
- **Business failure ≠ delivery failure.** A `DomainError` (duplicate code, role not found) is a *result*, recorded as
  `failed` and never retried — retrying cannot fix it. An exception (database down) *is* retried and eventually
  dead-lettered.
- **The operator travels in the message.** `WriteRequested.operator` is captured at the API (from the authenticated
  principal) and restored in the consumer, so audit columns name the real user, not the worker.
- **Secrets never enter the bus.** Operations that carry a clear-text password (`/user/add`, change-password,
  `/employee/add`) stay synchronous; Kafka messages are persisted.
- **Handlers are data.** `build_write_handlers` maps `"Entity.action"` to a handler; a test proves the set of handlers
  equals the set of commands the endpoints submit.

`pending` honestly means "no outcome recorded": not consumed yet, retrying, or dead-lettered.

## 8. Messaging

### 8.1 Abstraction

`EventBus` (publish / subscribe / start / stop) has three implementations behind `create_event_bus`:

| Bus | For | Properties |
|---|---|---|
| `memory` | tests, local | in-process; handlers run inside `publish`, so a write command executes synchronously |
| `redis` | small deployments | one Redis Stream, one consumer group, retry then leave in PEL |
| `kafka` | production scale | five domain topics, per-topic consumers, DLQ topics |

All three share a `HandlerRegistry` (subscription table, handler dispatch under a consumer `request_context`) and
`dispatch_with_retry` (3 attempts with growing delay), and one wire format: `{"event_type", "payload"}` JSON, decoded by
class name. Delivery is **at least once**, so every handler is written to be idempotent.

### 8.2 Kafka layout

- **Five topics by business domain** (`organization`, `identity`, `authorization`, `hr`, `config`). Commands and the
  events they cause share a topic, so everything about one domain is in one ordered log. Routing lives in
  `topics.py` and is complete-by-test.
- **Key = aggregate id** → per-aggregate ordering within a partition.
- **Producer**: `acks=all`, idempotent producer, `send_and_wait`.
- **Consumer**: one per topic, group `<group>.<topic>`, manual commit. Commit happens only after the message was handled
  or copied to `<topic>.dlq` (with source topic / partition / offset headers). No loss, and a poison message cannot block
  a partition.
- Topics (and their DLQs) are created at startup when enabled; production should create them explicitly.

### 8.3 Redis Streams layout

One stream (`XADD … MAXLEN ~`), one group, `XREADGROUP`, `XACK` after success; a failed message stays in the PEL. It is
simpler to run but has no per-aggregate ordering across parallel consumers and no DLQ — which is why Kafka is the
recommended bus when ordering or retention matters.

### 8.4 Domain-event consumers

Every domain event (except `WriteRequested`, whose outcome row *is* its audit record) is written to `sys_log` with a
`log_uuid` derived from `event_id`, so replays do not duplicate. `SysConfigChanged` evicts the configuration cache;
authority-affecting events bump the organization's authority-cache version (§9).

## 9. Caching

One `Cache` protocol (`get / set(ttl) / delete`), implemented by Redis (prefix, TTL) and by an in-process dict.

| Key | Use | Invalidation |
|---|---|---|
| `sys_config:<org>:<key>` | read-through configuration | event after commit |
| `session:<sha256(token)>` | login sessions | logout / TTL |
| `authz:<org>:<version>:<user>` | role + permission codes | version bump / short TTL |
| `authz_ver:<org>` | per-organization version | rewritten by events |

**Versioned keys instead of scanning.** A change to a role or permission affects an unknown set of users. Instead of
finding and deleting each key, the organization's version is replaced; old keys are simply never read again and expire.
This is O(1) and works the same on Redis and the in-memory cache. The short TTL (60 s) is the safety net if an event is
ever lost.

## 10. Authentication and authorization

### 10.1 Authentication

`POST /auth/login` checks the user (enabled), the password (scrypt with per-hash salt, constant-time compare), and the
tenant (enabled, not expired). It returns an **opaque random token**; the session (`user, org, tenant`) lives in the
cache keyed by the token's SHA-256. Reasons for opaque tokens over JWT: instant revocation (delete the key), no key
management, no stale claims — at the price of one cache read per request, which the cache is built for. Unknown user and
wrong password return the same error and cost the same hashing, so usernames cannot be probed.

A middleware turns `Authorization: Bearer …` into the **request context** (operator, user, org, tenant). Everything
downstream — audit columns, `WriteRequested.operator` — reads the context; nothing takes identity from a header or a
parameter.

### 10.2 Authorization

```
principal = session + authorities(user)           authorities(user) = union over ENABLED roles of permission codes
guard      = has_permission(*codes) | has_role(*roles) | authenticated()
decision   = any code granted (wildcards: "role:*", "*")   → 401 / 403
org check  = body.reqInfo.orgUuid must equal principal.org (unless platform org or "*")
```

- **Guards are FastAPI dependencies** attached to the route (`dependencies=[has_permission("role:add")]`) — the
  closest Python equivalent of a method-level annotation, visible in the route list and in Swagger (bearer scheme).
- **Permission codes, not role names, guard endpoints.** Which role holds which code is data (the permission tables), so
  changing grants never needs a deployment.
- **Tenant isolation is part of the guard.** The body is cached by Starlette, so the guard can read `orgUuid` before the
  endpoint runs. Without this, "may update roles" would mean "may update anyone's roles".
- **Menus are presentation, not security.** `/auth/me` returns the menu tree the user may see; calls are still
  authorized by their own guard.
- **Coverage is tested.** Every route must be guarded or be listed in `UNGUARDED_YET` / the public set, so a new
  endpoint cannot silently ship open.

## 11. Internationalization

Business errors are *values* made from English templates plus parameters. Translating at the edge keeps the domain
language-free:

1. `Accept-Language` is parsed by the middleware (highest `q`, supported primary subtag, configurable default) into a
   ContextVar and echoed as `Content-Language`.
2. When an error becomes an envelope, its formatted message is **matched back to its spec** (code *and* text must
   match, specific specs first, generic `not_found` last), the parameters are extracted, and the translated template from
   `messages.py` is filled in. Words such as entity names are translated as parameters.
3. Unknown messages fall back to English; codes (`errorCode`) never change.

Completeness is enforced by a test: every catalog spec needs a translation per language with compatible placeholders,
and stale translations fail. This design needed no change to `hiaok-core`; the cost is a regex match per error, paid only
on the (rare) failure path.

## 12. Configuration and deployment

- **pydantic-settings**, one class per concern (`APP_`, `AUTH_`, `DB_`, `REDIS_`, `KAFKA_`), layered `.env` →
  `.env.<APP_ENV>` → real environment.
- **Processes**: `hiaok` (API) and `hiaok worker`. Stateless; scale either side horizontally. Redis consumers need a
  unique `REDIS_CONSUMER_NAME` per replica; Kafka consumers scale by partitions.
- **Migrations** (Alembic) always run against the master. `update_time` is written by the ORM, not triggers.
- **docker-compose** brings up master + streaming-replica PostgreSQL, Redis, optional Kafka, migrate, api, worker.

## 13. Quality gates and productivity

- **Architecture tests** (layering, naming, error catalogs, relative imports), **route-guard coverage**, **write-handler
  coverage**, **topic-routing coverage**, **translation coverage**, **DDL document freshness** — all fail the build rather
  than rely on review.
- **Test layers**: pure unit tests (in-memory bus / cache, fakes instead of a database), integration tests that skip
  themselves when Redis / Kafka are unreachable. Test data comes from polyfactory factories that bypass validation.
- **Code generation**: a spec file (TOML) plus jinja2 meta templates generate the per-resource skeleton, because the
  shape is deliberately uniform. Templates are strict (undefined variables fail).
- Tooling: uv, ruff, pyright, pytest.

## 14. Trade-offs and known limitations

| Topic | Today | Consequence | If it hurts |
|---|---|---|---|
| All writes asynchronous | create/update/delete go through the bus | eventual consistency; callers poll `/log/get-by-request`; the bus is on the write path | keep CRUD synchronous, use asynchronous commands only for batch / long jobs |
| Events after commit | published after the root commit | a crash in between loses events | transactional **outbox** (write events in the same transaction, relay to the bus) |
| Dead-lettered commands | stay `pending` | manual replay from `.dlq` | a small replay tool; record dead-letter as a `failed` outcome |
| Redis bus | one stream, no DLQ, weak ordering | acceptable for small installs | use Kafka |
| Guard coverage | `role`, `menu`, `/auth/*` | other resources open | migrate resource by resource; `UNGUARDED_YET` shrinks |
| `/user/authorities` | unguarded | anyone can read anyone's authorities | guard: self or `user:authorities` |
| First administrator | created by hand with `AUTH_ENABLED=false` | bootstrap friction | seed script |
| Business errors are HTTP 200 | monitor by `code` | HTTP dashboards miss them | acceptable by design; export a `code` metric |
| Per-error regex for i18n | only on failures | negligible | move parameters into `DomainError` in `hiaok-core` |

## 15. Where to look

| Concern | Start here |
|---|---|
| Layer rules | `tests/unit/test_architecture.py` |
| Transactions | `src/infrastructure/database/routing.py`, `src/application/service/datasource.py` |
| Async writes | `src/application/usecase/command.py`, `src/application/service/command_service.py`, `src/application/service/ids.py` |
| Kafka / Redis | `src/infrastructure/messaging/` |
| Cache / sessions | `src/infrastructure/cache/`, `src/application/service/auth_service.py` |
| Authentication / guards | `src/application/usecase/auth.py`, `src/presentation/dependency/auth.py`, `src/presentation/middleware.py` |
| Errors / i18n | `src/presentation/exception.py`, `src/presentation/i18n.py`, `src/presentation/messages.py` |
| Authorization rules | `src/domain/service/authority.py` |
