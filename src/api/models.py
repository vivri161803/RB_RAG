"""
src/api/models.py
-----------------
Request/Response Pydantic models per l'API REST.
Separati dai modelli interni del KG — nessun embedding esposto.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════
# Shared
# ═══════════════════════════════════════════════════════════════


class AttributeOut(BaseModel):
    """Attributo esposto dall'API (senza embedding)."""

    name: str
    field_type: str
    description: str
    mandatory: bool


class ErrorResponse(BaseModel):
    """Risposta di errore standardizzata."""

    error: str
    detail: str
    status_code: int


# ═══════════════════════════════════════════════════════════════
# POST /route
# ═══════════════════════════════════════════════════════════════


class RouteRequest(BaseModel):
    description: str = Field(..., min_length=1, description="Descrizione testuale del prodotto/asset")


class RouteResponse(BaseModel):
    level1: str
    level2: str
    reason: str


# ═══════════════════════════════════════════════════════════════
# POST /extract
# ═══════════════════════════════════════════════════════════════


class ExtractRequest(BaseModel):
    level1: str = Field(..., min_length=1, description="Nome del Level1 (es. Immobili)")
    level2: str = Field(..., min_length=1, description="Nome del Level2 (es. Villa)")


class ExtractResponse(BaseModel):
    level1: str
    level2: str
    attributes: list[AttributeOut]
    count: int


# ═══════════════════════════════════════════════════════════════
# POST /run
# ═══════════════════════════════════════════════════════════════


class RunRequest(BaseModel):
    description: str = Field(..., min_length=1, description="Descrizione testuale del prodotto/asset")


from pydantic import ConfigDict


class RunResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    level1: str
    level2: str
    reason: str
    attributes_count: int
    json_schema: dict = Field(..., alias="schema", serialization_alias="schema")


# ═══════════════════════════════════════════════════════════════
# POST /build-kg
# ═══════════════════════════════════════════════════════════════


class BuildKGRequest(BaseModel):
    enrich: bool = Field(default=False, description="Genera descrizioni attributi via LLM")


class BuildKGResponse(BaseModel):
    status: str
    counts: dict


# ═══════════════════════════════════════════════════════════════
# GET /health
# ═══════════════════════════════════════════════════════════════


class HealthResponse(BaseModel):
    status: str
    neo4j: str
    timestamp: str
