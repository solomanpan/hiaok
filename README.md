# hiaok

A lightweight permission center: four DDD layers, event-driven (Kafka / Redis Streams), write-to-master / read-from-slave, bearer-token authorization with permission codes, localized errors (en / zh / ja).

| Language | Guide |
|---|---|
| English | [readme-en.md](readme-en.md) |
| 日本語 | [readme-jp.md](readme-jp.md) |
| 中文 | [readme-zh.md](readme-zh.md) |

Each guide covers: quick start · how to use the DDD framework · how authorization works · Kafka · Redis · i18n · API conventions · configuration · testing.

System design (English): [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · Meta-template code generation: [codegen/README.md](codegen/README.md) · Database DDL: [db.properties.md](db.properties.md)

## A DDD example, front to back

hiaok is meant to be read as well as run: a small but real system (RBAC, multi-organization, asynchronous writes, audit log, captcha, i18n) where **both the Python back end and the TypeScript front end follow DDD**, and where **tests enforce the dependency rules** on both sides — DDD as code you can check, not only as folder names.

| Repository | Role |
|---|---|
| [hiaok](https://github.com/solomanpan/hiaok) (this one) | Back end: Python 3.12 · FastAPI · SQLAlchemy 2 · Kafka / Redis Streams |
| [hiaok-core](https://github.com/solomanpan/hiaok-core) | Shared kernel: facades (Cache, EventBus, ...), error catalog, `Result` helpers, request context |
| [hiaok-web](https://github.com/solomanpan/hiaok-web) | Front end: one React Native (Expo) app for web, iOS, Android and desktop (Tauri), with a framework-free DDD core |

```
 hiaok-web                                     hiaok
┌─────────────────────────────────┐          ┌─────────────────────────────────┐
│ apps/app           UI (RN)      │          │ presentation    endpoints,      │
│    │                            │          │    │            guards          │
│    ▼                            │   HTTP   │    ▼                            │
│ core/application   use cases    │   POST   │ application     use cases,      │
│    │                            │ ───────▶ │    │            services        │
│    ▼                            │ /v1/api/ │    ▼                            │
│ core/domain        session,     │  hiaok/  │ domain          entities,       │
│    ▲               access, ports│  <res>/  │    ▲            rules           │
│    │                            │ <action> │    │                            │
│ core/infrastructure HTTP gateway│          │ infrastructure  DB, Kafka, Redis│
│    │                            │          └─────────────────────────────────┘
│ packages/api-client fetch       │                  uses hiaok-core
└─────────────────────────────────┘
  dependencies point inward on both sides (checked by architecture tests)
```

### Follow one request: signing in

```
hiaok-web
  Login.submit()                                apps/app/src/Auth.tsx
  → app.auth.signIn.execute(credentials)        core/application/usecases/auth.ts   (SignIn use case)
  → AuthGateway.login()                         core/domain/ports.ts                (port)
  → client.auth.login()                         core/infrastructure/http-gateway.ts (adapter)
  → client.call('auth', 'login', reqInfo)       packages/api-client/src/client.ts
      POST /v1/api/hiaok/auth/login   body {requestId, reqInfo}
hiaok
  login()                                       src/presentation/endpoint/auth.py
  → captcha_guard(captchaId, captchaCode)       one-time captcha (when enabled)
  → login use case                              src/application/usecase/auth.py
      find user → verify password (same cost for unknown users) → user enabled? → tenant active?
  → AuthService.issue(session)                  opaque token; the cache keeps session:<sha256(token)>
  ← {code: 0, resultInfo: {accessToken, expiresIn, userUuid}}
hiaok-web
  → SessionManager.update({token, ...})         persisted, listeners notified
  → React re-renders (useSyncExternalStore)
  → LoadAccess → POST auth/me (Bearer token)    roles, permission codes, menu tree
  → the menu and the buttons follow the permission codes (role:list, role:*, *)
```

Every later call carries `Authorization: Bearer <token>` and is checked by the endpoint's guard (`has_permission("role:add")`); a `401` signs the front end out. Writes are asynchronous: the API answers `accepted`, and the front end polls `log/get-by-request` until the command succeeded or failed (section 4.5 of the guides).

Where to start reading: back end — section 2 of the guides ("How to use this DDD framework"); front end — [hiaok-web's README](https://github.com/solomanpan/hiaok-web#readme) ("Follow one request" and "Adding a page").

### Design decisions and non-goals

Decisions:

- **Four DDD layers, checked by tests.** `presentation → application → domain ← infrastructure`; architecture tests fail when a layer imports the wrong way or a protected route has no guard.
- **Errors as values.** Use cases return `Result` (Expression); business errors are declared once in an error catalog (hiaok-core) and become localized envelope messages.
- **One envelope API.** Every call is `POST /v1/api/hiaok/<resource>/<action>` with `{requestId, reqInfo}`, answered by `{code, msg, resultInfo, errorCode}`.
- **Asynchronous writes, traceable by request id.** add / update / delete answer `accepted`; a consumer applies the command and records its outcome (`log/get-by-request`). Kafka or Redis Streams in production, an in-memory bus for local runs.
- **Write to master, read from slave**, chosen per service method (`@master` / `@slave`).
- **Opaque tokens, not JWT.** A random token whose session lives in the cache (`session:<sha256(token)>`): sign-out and disabling a user take effect at once, and permission changes evict the cached authorities. The price is a shared cache (Redis) when running several instances.
- **Permission codes on every route** (`role:add`, `role:*`, `*`), granted through roles; a new organization gets an `ORG_ADMIN` role holding one wildcard per resource (not the cross-organization `*`).
- **Isolation by organization**: a request for another organization is refused (`org_mismatch`) unless the caller belongs to the platform organization.

Not done, on purpose (it is a lightweight permission center):

- **No data (row-level) permissions** such as "own department only" or "created by me"; isolation stops at the organization.
- **Tenants are not an authorization boundary** inside an organization.
- A permission's `resource`, `action` and `permType` describe it; only `permCode` is matched by the guards. There is no catalog of the codes the routes use — they are typed by hand.
- **No refresh token**: a session lasts `AUTH_SESSION_TTL_SECONDS` (2 h by default).
- **Username + password only** (plus captcha): no SMS / e-mail codes, OAuth / SSO, or two-factor authentication; no login rate limit or lockout.
- **Self-registration is always open** (`user/register`, without roles); there is no per-organization switch.
- No JWT / JWKS for other services to verify tokens offline; they call `auth/me` or share the cache.

**中文**：hiaok 也是一个**前后端都采用 DDD** 的完整示例，后端为 Python，前端为 TypeScript / React Native，两边都用架构测试约束依赖方向。上面的图和登录调用链对应 [readme-zh.md](readme-zh.md) 第 2、3 节以及 hiaok-web 的 README。设计取舍：DDD 四层并用测试约束、错误即值（`Result`）、统一信封接口、按 requestId 追踪的异步写入、写主读从、不透明令牌（非 JWT，退出与停用即时生效）、每个接口一个权限码、按组织隔离。刻意不做：数据（行级）权限、组织内的租户隔离、权限码目录、refresh token、短信 / 第三方 / 双因素登录与登录限流、可关闭的自助注册、供其他服务离线验签的 JWT。

**日本語**：hiaok は**バックエンド（Python）とフロントエンド（TypeScript / React Native）の両方を DDD で書いた**実例でもあり、どちらも依存の向きをアーキテクチャテストで検証しています。上の図とログインの呼び出し経路は [readme-jp.md](readme-jp.md) の第 2・3 節と hiaok-web の README に対応します。設計上の選択: テストで守る DDD 4 層、値としてのエラー（`Result`）、統一エンベロープ API、requestId で追跡できる非同期書き込み、マスター書き込み／スレーブ読み取り、不透明トークン（JWT ではなく、ログアウトや無効化が即時に効く）、全エンドポイントの権限コード、組織単位の分離。意図的にやらないこと: データ（行レベル）権限、組織内のテナント分離、権限コードのカタログ、リフレッシュトークン、SMS／外部／二要素ログインとログイン回数制限、無効化できるセルフ登録、他サービスがオフライン検証できる JWT。

License: [MIT](LICENSE) © 2026 PAN JIE <sanbaikuai@gmail.com>
