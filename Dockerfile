# syntax=docker/dockerfile:1.7
# ---------------------------------------------------------------- build
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
# git: hiaok-core is a git dependency (public repo, no credentials needed)
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# dependencies first (cached layer, includes hiaok-core), then the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

# ---------------------------------------------------------------- runtime
FROM python:3.12-slim
RUN useradd --create-home --uid 1000 app
WORKDIR /app
COPY --from=builder --chown=app:app /app/.venv /app/.venv
# pyproject.toml carries the [tool.alembic] config used by `alembic upgrade head`
COPY --from=builder --chown=app:app /app/pyproject.toml /app/pyproject.toml
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 APP_ENV=docker
USER app
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"
CMD ["hiaok"]
