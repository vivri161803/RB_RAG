"""
src/routing/__init__.py
-----------------------
Phase 2 — Pipeline di routing completa.

Orchestrazione dei 3 step:
  1. LLM routing → Level1
  2. Vector search → top-K Level2
  3. LLM reranking → Level2 finale
"""

from __future__ import annotations

import logging

from neo4j import Driver

from src.routing.llm_router import route_level1
from src.routing.reranker import rerank_level2
from src.routing.vector_search import search_level2_candidates

logger = logging.getLogger(__name__)


def route(driver: Driver, description: str) -> tuple[str, str, str]:
    """Pipeline di routing completa: descrizione → (level1, level2, reason).

    Args:
        driver: Driver Neo4j connesso.
        description: Descrizione testuale del prodotto/asset.

    Returns:
        Tupla (level1_name, level2_name, reason).
    """
    # Step 1: LLM routing → Level1 + summary
    router_output = route_level1(driver, description)

    # Step 2: Vector search → top-K Level2
    candidates = search_level2_candidates(
        driver,
        level1_name=router_output.level1_id,
        summary=router_output.summary,
    )

    if not candidates:
        raise ValueError(
            f"Nessun Level2 trovato per Level1='{router_output.level1_id}'. "
            "Verifica che il KG sia stato costruito con build-kg."
        )

    # Step 3: LLM reranking → Level2 finale
    reranker_output = rerank_level2(description, candidates)

    logger.info(
        "Routing completato: %s → %s",
        router_output.level1_id,
        reranker_output.level2_id,
    )

    return router_output.level1_id, reranker_output.level2_id, reranker_output.reason
