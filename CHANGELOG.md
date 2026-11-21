# Changelog

All notable changes to hiaok. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [semantic versioning](https://semver.org/). Each release lists the database migrations to run (`uv run alembic upgrade head`) and anything that needs action when upgrading.

## [1.1.0] - 2026-11-21

### Added
- `hiaok bootstrap --org-code ... --org-name ... [--username] [--password]`: creates an organization, its default tenant, the `ORG_ADMIN` role and the first administrator in one transaction, with authentication left on. The password comes from `--password` or `HIAOK_ADMIN_PASSWORD`, else it is generated and printed once.
- Every route is guarded by a permission code (`<resource>:<endpoint>`); a new organization's `ORG_ADMIN` role is seeded with one wildcard per resource.
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md): minimum production setup (PostgreSQL + Redis, no Kafka), when to scale out, go-live checklist.
- [docs/INTEGRATION.md](docs/INTEGRATION.md): how your own services verify hiaok tokens and permissions.
- README: the DDD example front to back, the sign-in call chain, functional style in Python, design decisions and non-goals.
- GitHub Actions CI: ruff, pyright, pytest.

### Changed
- The guides no longer tell you to start with `AUTH_ENABLED=false` to create the first administrator.

### Upgrading
- No new migration. Routes that were open before 1.1.0 now answer `403 permission_denied` without the matching permission code: grant `<resource>:*` (or finer codes) to the roles that need them. Organizations provisioned before 1.1.0 keep the permissions they had; their administrators may need the new wildcards.

## [1.0] - 2026-11-18

### Added
- Lightweight permission center: organizations, tenants, users, user groups, projects, roles, permissions, menus, departments, employees, system configs and the audit log.
- Four DDD layers (presentation → application → domain ← infrastructure) with architecture tests; errors as values (`Result`) and error catalogs (hiaok-core v0.2.0).
- Envelope API: `POST /v1/api/hiaok/<resource>/<action>` with `{requestId, reqInfo}`.
- Asynchronous writes over Kafka, Redis Streams or an in-memory bus; outcomes looked up by request id (`log/get-by-request`).
- Bearer-token authentication (opaque tokens, server-side sessions), captcha, write-to-master / read-from-slave, localized messages (en / zh / ja), trilingual guides.

[1.1.0]: https://github.com/solomanpan/hiaok/compare/1.0...v1.1.0
[1.0]: https://github.com/solomanpan/hiaok/releases/tag/1.0
