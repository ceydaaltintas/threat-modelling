"""REST and SSE routers."""

from fastapi import APIRouter

from app.api import audit, health, kb, meta, projects, runs

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(meta.router)
api_router.include_router(projects.router)
api_router.include_router(runs.router)
api_router.include_router(kb.router)
api_router.include_router(audit.router)

__all__ = ["api_router"]
