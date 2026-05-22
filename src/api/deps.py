"""
src/api/deps.py
---------------
FastAPI dependency injection — Neo4j driver lifecycle.
"""

from __future__ import annotations

from neo4j import Driver

# Il driver Neo4j viene inizializzato nel lifespan dell'app
# e reso disponibile qui come singleton.
_driver: Driver | None = None


def set_driver(driver: Driver) -> None:
    """Imposta il driver Neo4j (chiamato dal lifespan)."""
    global _driver
    _driver = driver


def get_driver() -> Driver:
    """Dependency FastAPI: restituisce il driver Neo4j."""
    if _driver is None:
        raise RuntimeError("Driver Neo4j non inizializzato")
    return _driver
