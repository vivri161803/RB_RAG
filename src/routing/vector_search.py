"""
src/routing/vector_search.py
-----------------------------
Phase 2 — Step 2: Vector search cosine top-K.

Recupera i Level2 appartenenti al Level1 selezionato, calcola la cosine
similarity tra l'embedding del summary e il description_embedding di ogni
Level2, e restituisce i top-K candidati.
"""

from __future__ import annotations

import logging

import numpy as np
from neo4j import Driver

from src.config import get_settings
from src.kg.embedder import embed_text

logger = logging.getLogger(__name__)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calcola la cosine similarity tra due vettori."""
    va = np.array(a)
    vb = np.array(b)
    dot = np.dot(va, vb)
    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def _fetch_level2_by_level1(driver: Driver, level1_name: str) -> list[dict]:
    """Recupera i Level2 appartenenti al Level1 con i loro embedding."""
    records, _, _ = driver.execute_query(
        """
        MATCH (l2:Level2)-[:BELONGS_TO]->(l1:Level1 {name: $name})
        RETURN l2.name AS name, l2.description AS description,
               l2.description_embedding AS embedding
        """,
        name=level1_name,
    )
    return [
        {
            "name": r["name"],
            "description": r["description"],
            "embedding": r["embedding"],
        }
        for r in records
    ]


def search_level2_candidates(
    driver: Driver,
    level1_name: str,
    summary: str,
    top_k: int | None = None,
) -> list[tuple[str, str, float]]:
    """Step 2: vector search tra i Level2 del Level1 selezionato.

    Args:
        driver: Driver Neo4j connesso.
        level1_name: Nome del Level1 individuato dallo Step 1.
        summary: Riassunto dal RouterOutput.
        top_k: Numero di candidati da restituire (default da settings).

    Returns:
        Lista di (level2_name, level2_description, score) ordinata per score decrescente.
    """
    settings = get_settings()
    if top_k is None:
        top_k = settings.TOP_K

    # Recupera tutti i Level2 del Level1
    level2_nodes = _fetch_level2_by_level1(driver, level1_name)
    logger.info("Vector search — %d Level2 trovati per %s", len(level2_nodes), level1_name)

    if not level2_nodes:
        logger.warning("Nessun Level2 trovato per Level1=%s", level1_name)
        return []

    # Genera embedding del summary
    summary_embedding = embed_text(summary)

    # Calcola cosine similarity
    scored = []
    for node in level2_nodes:
        emb = node.get("embedding")
        if not emb:
            logger.debug("  Level2 %s senza embedding, skip", node["name"])
            continue
        score = _cosine_similarity(summary_embedding, emb)
        scored.append((node["name"], node["description"], score))

    # Ordina per score decrescente e prendi top-K
    scored.sort(key=lambda x: x[2], reverse=True)
    top = scored[:top_k]

    for name, _, score in top:
        logger.info("  → %s (score: %.4f)", name, score)

    return top
