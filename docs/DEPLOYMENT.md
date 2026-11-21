# Deploying hiaok

## Minimum production setup: PostgreSQL + Redis

Kafka is **not** required. Redis serves as the cache (sessions, authorities, configs) and as the event bus (Redis Streams), which is also the default (`APP_BROKER=redis`, `APP_CACHE=redis`).

```
            ┌──────────────┐
 clients ──▶│  hiaok (API) │──▶ PostgreSQL   (one primary is enough; a replica is optional)
            │  consumes    │──▶ Redis        (cache + event stream)
            │  its events  │
            └──────────────┘
```

One process runs the API and consumes the events itself (`APP_CONSUME_EVENTS=true`, the default). Without a replica, leave `DB_SLAVE_URL` unset: reads go to the primary.

```bash
export DB_MASTER_URL=postgresql+asyncpg://hiaok:<password>@db:5432/hiaok
export REDIS_URL=redis://redis:6379/0
export APP_CORS_ORIGINS=https://console.example.com
uv run alembic upgrade head                                                # schema, always on the primary
uv run hiaok bootstrap --org-code ACME --org-name "Acme" --username admin  # first administrator, auth stays on
uv run hiaok                                                               # API on :8000
```

With Docker Compose: `docker compose up -d --build` starts primary + replica, Redis, the migration, the API and a worker; create the first administrator with `docker compose run --rm api hiaok bootstrap --org-code ACME --org-name "Acme"`.

## Why writes are asynchronous, and what it costs

add / update / delete answer `accepted`; a consumer applies the command and records its outcome under the request id (`log/get-by-request`), which the console polls. This keeps one write path for every deployment — in-process, Redis Streams or Kafka — gives every command an audit record, and lets writes be retried and scaled apart from the API.

For a small deployment the cost is low: with the default single process the command is consumed in-process and its outcome is usually ready within milliseconds. What you do have to accept is that a write is not visible in the same HTTP response; clients wait for the outcome (the console and `api-client`'s `write()` do it for you).

## When to scale out

| Need | Change |
|---|---|
| More API throughput | Several API instances behind a load balancer. **Redis is required** (`APP_CACHE=redis`): sessions live in the cache. |
| Consume apart from the API | `APP_CONSUME_EVENTS=false` on API nodes and one or more `hiaok worker` processes (give each worker its own `REDIS_CONSUMER_NAME`). |
| Read load on the database | A streaming replica and `DB_SLAVE_URL`; `@slave` methods read from it. |
| Many writes, replay, several consumers of the events | `APP_BROKER=kafka` and `KAFKA_BOOTSTRAP_SERVERS` (`docker compose --profile kafka up -d`). Topics and dead-letter topics are created at startup. |

`APP_BROKER=memory` and `APP_CACHE=memory` are for local runs and tests only: a restart drops every session, and nothing is shared between processes.

## Go-live checklist

- [ ] `AUTH_ENABLED=true` (the default). `false` lets every call through — never in production.
- [ ] The first administrator created with `hiaok bootstrap`, the generated password changed after the first sign-in (or passed through `HIAOK_ADMIN_PASSWORD` from a secret store).
- [ ] `AUTH_PLATFORM_ORG_UUID` set only if one organization must manage all others.
- [ ] `APP_CORS_ORIGINS` lists only your console origins.
- [ ] `AUTH_CAPTCHA_ENABLED=true` when sign-in and self-registration (`user/register`, always open) face the internet; add a rate limit at the reverse proxy — hiaok has none.
- [ ] `APP_DOCS_ENABLED=false` unless `/docs` should be public.
- [ ] TLS terminated at the reverse proxy; tokens are bearer secrets.
- [ ] Database and Redis credentials from a secret store, not from the image.
- [ ] `alembic upgrade head` run before starting a new version (the Compose `migrate` service does it).
- [ ] `AUTH_SESSION_TTL_SECONDS` chosen on purpose (default 2 h, no refresh token).
- [ ] `GET /health` wired to the load balancer / orchestrator probes.
