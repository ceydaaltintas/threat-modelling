"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import api_router
from app.core.config import get_settings
from app.core.db import engine
from app.kb import loader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s | %(message)s",
)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(
        "Baslatiliyor: %s (env=%s, demo_replay=%s, ocr=%s)",
        settings.app_name,
        settings.app_env,
        settings.demo_replay,
        settings.ocr_enabled,
    )
    # The knowledge base ships pre-processed; load it once into Postgres.
    try:
        stats = await loader.ensure_loaded()
        logger.info("Bilgi tabani: %s kayit", stats["total"])
    except Exception:  # noqa: BLE001 - the app must still start
        logger.exception("Bilgi tabani yuklenemedi")
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "Mimari dokumanlardan tehdit modeli ureten demo platform. "
            "Sonuclar olasiliklardir; sistem testi yerine gecmez."
        ),
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    return app


app = create_app()
