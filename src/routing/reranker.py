"""
src/routing/reranker.py
-----------------------
Phase 2 — Step 3: LLM reranking.

Mostra i top-K Level2 candidati (dalla vector search) all'LLM
e gli chiede di scegliere il più adeguato alla descrizione originale.
"""

from __future__ import annotations

import logging

from src.config import get_instructor_client, get_settings
from src.models import RerankerOutput

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """\
Sei un esperto classificatore di asset italiani.

Ti vengono forniti una descrizione di un prodotto/asset e una lista di sotto-categorie
candidate. Devi scegliere la sotto-categoria più adeguata.

I candidati sono:

{candidates}

Rispondi con il `level2_id` esatto (uno dei nomi elencati) e una breve motivazione.
"""


def rerank_level2(
    description: str,
    candidates: list[tuple[str, str, float]],
) -> RerankerOutput:
    """Step 3: LLM reranking dei candidati Level2.

    Args:
        description: Descrizione originale del prodotto/asset.
        candidates: Lista di (level2_name, level2_description, score) dal vector search.

    Returns:
        RerankerOutput con level2_id e reason.
    """
    client = get_instructor_client()
    settings = get_settings()

    candidates_text = "\n".join(
        f"- **{name}** (similarity: {score:.3f}): {desc}"
        for name, desc, score in candidates
    )

    system_prompt = SYSTEM_PROMPT.format(candidates=candidates_text)

    logger.info("LLM reranking — selezione Level2 tra %d candidati...", len(candidates))
    result = client.chat.completions.create(
        model=settings.LLM_MODEL,
        response_model=RerankerOutput,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Descrizione prodotto:\n{description}"},
        ],
        extra_body={"provider": {"sort": "throughput"}},
        max_retries=2,
    )

    logger.info("  → Level2 scelto: %s", result.level2_id)
    logger.info("  → Reason: %s", result.reason[:80])
    return result
