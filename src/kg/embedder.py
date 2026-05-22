"""
src/kg/embedder.py
------------------
Generazione embedding e deduplicazione entità post-estrazione LLM.
Utilizza il modello di embedding configurato in .env via OpenRouter.
"""

from __future__ import annotations

import logging

import numpy as np

from src.config import get_openai_client, get_settings
from src.models import KGraph

logger = logging.getLogger(__name__)


# ── Embedding ────────────────────────────────────────────────


def embed_text(text: str) -> list[float]:
    """Genera l'embedding di un singolo testo via OpenRouter."""
    client = get_openai_client()
    settings = get_settings()

    response = client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=text,
        extra_body={"provider": {"sort": "throughput"}},
    )
    return response.data[0].embedding


def embed_batch(texts: list[str], batch_size: int = 64) -> list[list[float]]:
    """Genera embedding in batch per efficienza.

    OpenRouter/OpenAI accettano fino a 2048 input per chiamata,
    ma usiamo batch più piccoli per sicurezza.
    """
    client = get_openai_client()
    settings = get_settings()
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        logger.debug("Embedding batch %d-%d di %d", i, i + len(batch), len(texts))

        response = client.embeddings.create(
            model=settings.EMBEDDING_MODEL,
            input=batch,
            extra_body={"provider": {"sort": "throughput"}},
        )
        # Ordina per index per garantire l'ordine
        sorted_data = sorted(response.data, key=lambda x: x.index)
        all_embeddings.extend([d.embedding for d in sorted_data])

    return all_embeddings


# ── Cosine Similarity ────────────────────────────────────────


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calcola la cosine similarity tra due vettori."""
    va = np.array(a)
    vb = np.array(b)
    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))


# ── Popolamento embedding nel KGraph ─────────────────────────


def populate_embeddings(kg: KGraph) -> KGraph:
    """Popola gli embedding di tutti i nodi del KGraph.

    - Level1: name_embedding = embed(id)
    - Level2: description_embedding = embed(description)
    - Attribute: name_embedding = embed(name)
    """
    # Level1 — embed id
    l1_texts = [n.name for n in kg.level1_nodes]
    if l1_texts:
        logger.info("Embedding %d nodi Level1...", len(l1_texts))
        l1_embeddings = embed_batch(l1_texts)
        for node, emb in zip(kg.level1_nodes, l1_embeddings):
            node.name_embedding = emb

    # Level2 — embed description
    l2_texts = [n.description for n in kg.level2_nodes]
    if l2_texts:
        logger.info("Embedding %d nodi Level2...", len(l2_texts))
        l2_embeddings = embed_batch(l2_texts)
        for node, emb in zip(kg.level2_nodes, l2_embeddings):
            node.description_embedding = emb

    # Attribute — embed name
    attr_texts = [n.name for n in kg.attributes]
    if attr_texts:
        logger.info("Embedding %d nodi Attribute...", len(attr_texts))
        attr_embeddings = embed_batch(attr_texts)
        for node, emb in zip(kg.attributes, attr_embeddings):
            node.name_embedding = emb

    logger.info("Embedding completati per tutti i nodi")
    return kg


# ── Deduplicazione attributi per similarità ──────────────────


def deduplicate_attributes(kg: KGraph, threshold: float = 0.95) -> KGraph:
    """Deduplicazione degli attributi con cosine similarity > threshold.

    Per ogni coppia di attributi con nomi simili, mantiene il primo e
    aggiorna tutte le triple per puntare al nome canonico.
    """
    if len(kg.attributes) < 2:
        return kg

    # Serve che gli embedding siano già popolati
    attrs_with_emb = [a for a in kg.attributes if a.name_embedding]
    if not attrs_with_emb:
        logger.warning("Nessun attributo con embedding, skip deduplicazione")
        return kg

    # Mappa nome → nome canonico
    canonical: dict[str, str] = {}
    merged_count = 0

    for i, a in enumerate(attrs_with_emb):
        if a.name in canonical:
            continue
        canonical[a.name] = a.name  # self-mapping

        for b in attrs_with_emb[i + 1 :]:
            if b.name in canonical:
                continue
            sim = cosine_similarity(a.name_embedding, b.name_embedding)
            if sim >= threshold:
                canonical[b.name] = a.name
                merged_count += 1
                logger.debug(
                    "Merge attributo '%s' → '%s' (sim=%.3f)", b.name, a.name, sim
                )

    if merged_count == 0:
        logger.info("Nessun attributo duplicato trovato (threshold=%.2f)", threshold)
        return kg

    logger.info("Deduplicati %d attributi (threshold=%.2f)", merged_count, threshold)

    # Filtra attributi mantenendo solo i canonici
    canonical_names = set(canonical.values())
    kg.attributes = [a for a in kg.attributes if a.name in canonical_names]

    # Aggiorna le triple per usare i nomi canonici
    for triple in kg.triples_requires_l1:
        if triple.target in canonical:
            triple.target = canonical[triple.target]

    for triple in kg.triples_requires_l2:
        if triple.target in canonical:
            triple.target = canonical[triple.target]

    return kg
