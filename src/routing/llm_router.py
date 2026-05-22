"""
src/routing/llm_router.py
-------------------------
Phase 2 — Step 1: LLM routing per identificare il Level1 corretto.

Mostra le 3 macro-categorie all'LLM e chiede di identificare quella più
adeguata alla descrizione del prodotto, generando anche un riassunto breve.
"""

from __future__ import annotations

import logging

from neo4j import Driver

from src.config import get_instructor_client, get_settings
from src.models import RouterOutput

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """\
Sei un esperto classificatore di asset immobiliari, aziendali e commerciali italiani.

Data la descrizione di un prodotto/asset, devi:
1. Identificare la macro-categoria (Level1) più adeguata tra quelle elencate.
2. Scrivere un riassunto conciso (max 100 parole) che evidenzi le caratteristiche
   rilevanti del prodotto per facilitare l'identificazione della sotto-categoria.

Le macro-categorie disponibili sono:

{categories}

Rispondi con il `level1_id` esatto (uno dei nomi elencati) e il `summary`.
"""


def _fetch_level1_nodes(driver: Driver) -> list[dict]:
    """Recupera i nodi Level1 con name e description da Neo4j."""
    records, _, _ = driver.execute_query(
        "MATCH (n:Level1) RETURN n.name AS name, n.description AS description"
    )
    return [{"name": r["name"], "description": r["description"]} for r in records]


def route_level1(driver: Driver, description: str) -> RouterOutput:
    """Step 1: classifica la descrizione in una macro-categoria (Level1).

    Args:
        driver: Driver Neo4j connesso.
        description: Descrizione testuale del prodotto/asset.

    Returns:
        RouterOutput con level1_id e summary.
    """
    client = get_instructor_client()
    settings = get_settings()

    # Recupera le categorie dal KG
    categories = _fetch_level1_nodes(driver)
    categories_text = "\n".join(
        f"- **{c['name']}**: {c['description']}" for c in categories
    )

    system_prompt = SYSTEM_PROMPT.format(categories=categories_text)

    logger.info("LLM routing — identificazione Level1...")
    result = client.chat.completions.create(
        model=settings.LLM_MODEL,
        response_model=RouterOutput,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Descrizione prodotto:\n{description}"},
        ],
        extra_body={"provider": {"sort": "throughput"}},
        max_retries=2,
    )

    logger.info("  → Level1: %s", result.level1_id)
    logger.info("  → Summary: %s", result.summary[:80] + "...")
    return result
