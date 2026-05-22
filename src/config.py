"""
src/config.py
-------------
Configurazione centralizzata dell'applicazione.
Carica le variabili d'ambiente da .env tramite pydantic-settings.
"""

from __future__ import annotations

from functools import lru_cache

import instructor
from neo4j import GraphDatabase
from openai import OpenAI
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurazione applicativa caricata da .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Neo4j ──────────────────────────────────────────────
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = ""

    # ── OpenRouter ─────────────────────────────────────────
    API: str  # chiave OpenRouter (obbligatoria)
    LLM_MODEL: str = "openai/gpt-oss-20b"
    EMBEDDING_MODEL: str = "openai/text-embedding-3-small"

    # ── Pipeline ───────────────────────────────────────────
    TOP_K: int = 5


@lru_cache
def get_settings() -> Settings:
    """Singleton delle impostazioni (cached)."""
    return Settings()


# ── Factory helpers ──────────────────────────────────────────


def get_openai_client() -> OpenAI:
    """Client OpenAI puntato su OpenRouter."""
    s = get_settings()
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=s.API,
    )


def get_instructor_client() -> instructor.Instructor:
    """Client Instructor wrappato su OpenRouter (modalità JSON per compatibilità)."""
    return instructor.from_openai(
        get_openai_client(),
        mode=instructor.Mode.JSON,
    )


def get_neo4j_driver():
    """Driver Neo4j."""
    s = get_settings()
    return GraphDatabase.driver(
        s.NEO4J_URI,
        auth=(s.NEO4J_USERNAME, s.NEO4J_PASSWORD),
    )


# Shortcut per import diretto
settings = get_settings()
