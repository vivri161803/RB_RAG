"""
src/api/app.py
--------------
FastAPI application con lifespan Neo4j e exception handlers globali.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.deps import set_driver
from src.api.routes import router
from src.config import get_neo4j_driver

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Gestione lifecycle: crea il driver Neo4j allo startup, chiude allo shutdown."""
    # Startup
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
        datefmt="%H:%M:%S",
    )
    logger.info("Avvio Rules Retrieval API...")

    try:
        driver = get_neo4j_driver()
        set_driver(driver)
        logger.info("Driver Neo4j connesso")
    except Exception as e:
        logger.error("Impossibile connettersi a Neo4j: %s", e)
        raise

    yield

    # Shutdown
    logger.info("Shutdown — chiusura driver Neo4j")
    driver.close()


app = FastAPI(
    title="Rules Retrieval API",
    description="Pipeline di routing e validazione regole per asset immobiliari, aziendali e commerciali.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — uso interno, allow all
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include il router
app.include_router(router)


# ═══════════════════════════════════════════════════════════════
# Exception handlers globali
# ═══════════════════════════════════════════════════════════════


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all per errori non gestiti."""
    logger.exception("Errore non gestito: %s", exc)

    # Neo4j connection errors
    exc_type = type(exc).__name__
    if "ServiceUnavailable" in exc_type or "Neo4j" in exc_type:
        return JSONResponse(
            status_code=503,
            content={
                "error": "Neo4jConnectionError",
                "detail": f"Impossibile connettersi a Neo4j: {exc}",
                "status_code": 503,
            },
        )

    # OpenRouter / OpenAI errors
    if "APIError" in exc_type or "APIConnectionError" in exc_type:
        return JSONResponse(
            status_code=502,
            content={
                "error": "OpenRouterError",
                "detail": f"Errore comunicazione con OpenRouter: {exc}",
                "status_code": 502,
            },
        )

    # Generico
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "detail": str(exc),
            "status_code": 500,
        },
    )
