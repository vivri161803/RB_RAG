"""
src/api/routes.py
-----------------
Definizione degli endpoint REST.
Ogni endpoint è un thin wrapper sulle funzioni core esistenti.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from neo4j import Driver

from src.api.deps import get_driver
from src.api.models import (
    AttributeOut,
    BuildKGRequest,
    BuildKGResponse,
    ExtractRequest,
    ExtractResponse,
    HealthResponse,
    RouteRequest,
    RouteResponse,
    RunRequest,
    RunResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ═══════════════════════════════════════════════════════════════
# GET /health
# ═══════════════════════════════════════════════════════════════


@router.get("/health", response_model=HealthResponse)
def health(driver: Driver = Depends(get_driver)):
    """Health check: verifica connessione Neo4j."""
    try:
        driver.execute_query("RETURN 1")
        neo4j_status = "connected"
    except Exception as e:
        neo4j_status = f"disconnected: {e}"

    status = "healthy" if neo4j_status == "connected" else "unhealthy"
    return HealthResponse(
        status=status,
        neo4j=neo4j_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# ═══════════════════════════════════════════════════════════════
# POST /route
# ═══════════════════════════════════════════════════════════════


@router.post("/route", response_model=RouteResponse)
def route_endpoint(req: RouteRequest, driver: Driver = Depends(get_driver)):
    """Routing: descrizione → Level1 + Level2."""
    from src.routing import route

    logger.info("API /route — description: %s", req.description[:60])
    level1, level2, reason = route(driver, req.description)
    return RouteResponse(level1=level1, level2=level2, reason=reason)


# ═══════════════════════════════════════════════════════════════
# POST /extract
# ═══════════════════════════════════════════════════════════════


@router.post("/extract", response_model=ExtractResponse)
def extract_endpoint(req: ExtractRequest, driver: Driver = Depends(get_driver)):
    """Estrazione: Level1 + Level2 → attributi."""
    from src.extractor import extract_rules

    logger.info("API /extract — %s → %s", req.level1, req.level2)
    attributes = extract_rules(driver, req.level1, req.level2)

    attrs_out = [
        AttributeOut(
            name=a.name,
            field_type=a.field_type,
            description=a.description,
            mandatory=a.mandatory,
        )
        for a in attributes
    ]

    return ExtractResponse(
        level1=req.level1,
        level2=req.level2,
        attributes=attrs_out,
        count=len(attrs_out),
    )


# ═══════════════════════════════════════════════════════════════
# POST /run
# ═══════════════════════════════════════════════════════════════


@router.post("/run", response_model=RunResponse)
def run_endpoint(req: RunRequest, driver: Driver = Depends(get_driver)):
    """Pipeline completa: descrizione → JSON Schema."""
    from src.extractor import extract_rules
    from src.routing import route
    from src.schema_builder import build_schema, export_json_schema

    logger.info("API /run — description: %s", req.description[:60])

    # Phase 2: Routing
    level1, level2, reason = route(driver, req.description)

    # Phase 3: Extraction
    attributes = extract_rules(driver, level1, level2)

    # Phase 4: Schema Builder
    model = build_schema(attributes)
    schema = export_json_schema(model)

    return RunResponse(
        level1=level1,
        level2=level2,
        reason=reason,
        attributes_count=len(attributes),
        json_schema=schema,
    )


# ═══════════════════════════════════════════════════════════════
# POST /build-kg
# ═══════════════════════════════════════════════════════════════


@router.post("/build-kg", response_model=BuildKGResponse)
def build_kg_endpoint(req: BuildKGRequest, driver: Driver = Depends(get_driver)):
    """Trigger rebuild del Knowledge Graph."""
    from src.kg.builder import build_kg
    from src.kg.embedder import populate_embeddings
    from src.kg.neo4j_loader import clear_graph, create_constraints, load_graph

    logger.info("API /build-kg — enrich=%s", req.enrich)

    # Build
    kg = build_kg("rules/rules.json", enrich=req.enrich)
    kg = populate_embeddings(kg)

    # Load
    clear_graph(driver)
    create_constraints(driver)
    counts = load_graph(driver, kg)

    return BuildKGResponse(status="completed", counts=counts)
