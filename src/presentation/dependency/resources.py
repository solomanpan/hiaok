"""Process-wide resources (opened in the FastAPI lifespan)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from ...infrastructure.resources import Resources


def get_resources(request: Request) -> Resources:
    return request.app.state.resources


ResourcesDep = Annotated[Resources, Depends(get_resources)]
