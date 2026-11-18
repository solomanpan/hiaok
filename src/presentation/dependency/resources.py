"""Process-wide resources (opened in the FastAPI lifespan) and request paging."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Query, Request

from ...domain.repository import PageQuery
from ...infrastructure.resources import Resources


def get_resources(request: Request) -> Resources:
    return request.app.state.resources


ResourcesDep = Annotated[Resources, Depends(get_resources)]


def page_query(offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=200)) -> PageQuery:
    return PageQuery(offset, limit)


PageDep = Annotated[PageQuery, Depends(page_query)]
