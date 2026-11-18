from fastapi import APIRouter

from ..dependency import ResourcesDep

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(r: ResourcesDep) -> dict[str, str | bool]:
    """Pings both datasources; ``slave_in_recovery=true`` means reads really go to a replica."""
    return await r.db.ping()
