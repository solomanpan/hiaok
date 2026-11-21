"""Entry point.

uvicorn src.main:app --reload       # API
hiaok                                 # API (uvicorn, settings from env / .env.<APP_ENV>)
hiaok worker                          # event consumer only (scale independently)
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import anyio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .application.config import Settings, get_settings
from .application.service import CommandService, SysLogService
from .application.usecase.command import write_handler
from .application.usecase.event_handler import subscribe_event_handlers
from .infrastructure.repository import SqlSysLogRepository
from .infrastructure.resources import Resources, build_resources, open_resources
from .presentation.dependency import build_write_handlers
from .presentation.endpoint import api_router, health
from .presentation.exception import install_exception_handlers
from .presentation.middleware import install_context_middleware
from .presentation.openapi import (
    API_VERSION,
    DESCRIPTION,
    OPENAPI_TAGS,
    SWAGGER_UI_PARAMETERS,
    operation_id,
)

log = logging.getLogger("hiaok")


def wire_event_handlers(resources: Resources) -> None:
    """Consumers: WriteRequested -> run the usecase + record the outcome; every other domain event -> sys_log;
    SysConfigChanged -> evict cache."""
    logs = SysLogService(resources.tx, SqlSysLogRepository(resources.db))
    commands = CommandService(resources.tx, logs)
    on_write = write_handler(commands, build_write_handlers(resources))
    subscribe_event_handlers(resources.bus, logs, resources.cache, on_write)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=settings.app.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        resources = build_resources(settings)
        if settings.app.consume_events:
            wire_event_handlers(resources)
        async with open_resources(resources):
            app.state.resources = resources
            log.info(
                "hiaok started (env=%s broker=%s cache=%s consume_events=%s)",
                settings.app.env,
                settings.app.broker,
                settings.app.cache,
                settings.app.consume_events,
            )
            yield

    docs = settings.app.docs_enabled
    app = FastAPI(
        title=settings.app.name,
        version=API_VERSION,
        summary="Lightweight permission center",
        description=DESCRIPTION,
        openapi_tags=OPENAPI_TAGS,
        generate_unique_id_function=operation_id,
        swagger_ui_parameters=SWAGGER_UI_PARAMETERS,
        docs_url="/docs" if docs else None,
        redoc_url="/redoc" if docs else None,
        openapi_url="/openapi.json" if docs else None,
        lifespan=lifespan,
    )
    install_context_middleware(app)
    install_exception_handlers(app)
    if settings.app.cors_origin_list:  # the web / desktop / mobile console (hiaok-web) calls the API cross-origin
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.app.cors_origin_list,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Request-Id", "X-Operator", "Accept-Language"],
            expose_headers=["X-Request-Id", "Content-Language"],
        )
    app.include_router(health.router)
    app.include_router(api_router)
    return app


async def run_worker(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    logging.basicConfig(level=settings.app.log_level)
    resources = build_resources(settings)
    wire_event_handlers(resources)
    async with open_resources(resources):
        log.info("hiaok worker consuming (broker=%s)", settings.app.broker)
        await anyio.sleep_forever()


def run_api() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.main:app", host=settings.app.host, port=settings.app.port, log_level=settings.app.log_level.lower()
    )


app = create_app()
