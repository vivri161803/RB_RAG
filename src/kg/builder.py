"""
src/kg/builder.py
-----------------
Phase 1 — Costruzione deterministica del KGraph da rules.json.

Parsing deterministico del JSON strutturato per estrarre entità e triple.
L'LLM viene usato solo per decorare le entità con descrizioni arricchite
(opzionale, controllato dal flag --enrich-descriptions).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from src.config import get_instructor_client, get_settings
from src.models import AttributeNode, KGraph, Level1Node, Level2Node, Triple

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Parsing deterministico
# ═══════════════════════════════════════════════════════════════


def load_rules(path: str | Path) -> list[dict]:
    """Carica rules.json e restituisce la lista `categories`."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File non trovato: {path}")

    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    categories = data.get("categories", [])
    if not categories:
        raise ValueError("Il file JSON non contiene 'categories'")

    logger.info("Caricate %d macro-categorie da %s", len(categories), path)
    return categories


def _infer_field_type(name: str) -> str:
    """Inferisce il tipo del campo dal nome."""
    lower = name.lower()
    if any(kw in lower for kw in ("mq", "ha", "km", "€", "(ml)", "(m)", "mc", "rate")):
        return "float"
    if any(kw in lower for kw in ("(n.)", "numero", "posti", "piani", "camere", "bagni")):
        return "int"
    if "sì/no" in lower:
        return "bool"
    return "str"


def parse_kg(categories: list[dict]) -> KGraph:
    """Parsing deterministico: estrae entità e triple dal JSON strutturato.

    Nessuna chiamata LLM — estrae tutto dal JSON.
    """
    kg = KGraph()
    seen_attrs: dict[str, AttributeNode] = {}  # nome → nodo (per deduplicazione)

    for cat in categories:
        cat_name = cat["id"]
        cat_desc = cat.get("description", "")

        # ── Level1 ────────────────────────────────────────
        kg.level1_nodes.append(Level1Node(name=cat_name, description=cat_desc))

        # ── Attributi L1 (mandatory) ──────────────────────
        for field_name in cat.get("mandatory_fields", []):
            if field_name not in seen_attrs:
                seen_attrs[field_name] = AttributeNode(
                    name=field_name,
                    field_type=_infer_field_type(field_name),
                    mandatory=True,
                )
            kg.triples_requires_l1.append(Triple(source=cat_name, target=field_name))

        # ── Attributi L1 (optional) ───────────────────────
        for field_name in cat.get("optional_fields", []):
            if field_name not in seen_attrs:
                seen_attrs[field_name] = AttributeNode(
                    name=field_name,
                    field_type=_infer_field_type(field_name),
                    mandatory=False,
                )
            kg.triples_requires_l1.append(Triple(source=cat_name, target=field_name))

        # ── Level2 + Attributi L2 ─────────────────────────
        for sub in cat.get("sub_categories", []):
            sub_name = sub["id"]
            sub_desc = sub.get("description", "")

            kg.level2_nodes.append(Level2Node(name=sub_name, description=sub_desc))
            kg.triples_belongs_to.append(Triple(source=sub_name, target=cat_name))

            for field_name in sub.get("mandatory_fields", []):
                if field_name not in seen_attrs:
                    seen_attrs[field_name] = AttributeNode(
                        name=field_name,
                        field_type=_infer_field_type(field_name),
                        mandatory=True,
                    )
                kg.triples_requires_l2.append(Triple(source=sub_name, target=field_name))

            for field_name in sub.get("optional_fields", []):
                if field_name not in seen_attrs:
                    seen_attrs[field_name] = AttributeNode(
                        name=field_name,
                        field_type=_infer_field_type(field_name),
                        mandatory=False,
                    )
                kg.triples_requires_l2.append(Triple(source=sub_name, target=field_name))

    kg.attributes = list(seen_attrs.values())

    logger.info(
        "Parsing deterministico: %d L1, %d L2, %d attributi, %d triple",
        len(kg.level1_nodes),
        len(kg.level2_nodes),
        len(kg.attributes),
        len(kg.triples_belongs_to) + len(kg.triples_requires_l1) + len(kg.triples_requires_l2),
    )
    return kg


# ═══════════════════════════════════════════════════════════════
# Decorazione LLM delle descrizioni (opzionale)
# ═══════════════════════════════════════════════════════════════

from pydantic import BaseModel, Field


class AttributeDescriptions(BaseModel):
    """Descrizioni generate dall'LLM per un batch di attributi."""

    descriptions: list[str] = Field(
        ...,
        description="Lista di descrizioni (una per attributo, nello stesso ordine dell'input)",
    )


def enrich_attribute_descriptions(kg: KGraph, batch_size: int = 50) -> KGraph:
    """Usa l'LLM per generare descrizioni per gli attributi che ne sono privi.

    Processa in batch per ridurre il numero di chiamate API.
    """
    client = get_instructor_client()
    settings = get_settings()

    # Filtra solo gli attributi senza descrizione
    attrs_to_enrich = [a for a in kg.attributes if not a.description]
    if not attrs_to_enrich:
        logger.info("Tutti gli attributi hanno già una descrizione")
        return kg

    logger.info("Arricchimento descrizioni per %d attributi...", len(attrs_to_enrich))

    for i in range(0, len(attrs_to_enrich), batch_size):
        batch = attrs_to_enrich[i : i + batch_size]
        names_list = "\n".join(f"- {a.name} (tipo: {a.field_type})" for a in batch)

        result = client.chat.completions.create(
            model=settings.LLM_MODEL,
            response_model=AttributeDescriptions,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Sei un esperto di dominio immobiliare/aziendale italiano. "
                        "Per ogni attributo fornito, genera una descrizione concisa (max 20 parole) "
                        "che spieghi cosa rappresenta nel contesto di una scheda prodotto. "
                        "Restituisci esattamente una descrizione per attributo, nello stesso ordine."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Genera le descrizioni per questi attributi:\n{names_list}",
                },
            ],
            extra_body={"provider": {"sort": "throughput"}},
            max_retries=2,
        )

        # Assegna le descrizioni
        for attr, desc in zip(batch, result.descriptions):
            attr.description = desc

        logger.info("  Batch %d-%d: %d descrizioni generate", i, i + len(batch), len(batch))

    return kg


# ═══════════════════════════════════════════════════════════════
# Pipeline principale
# ═══════════════════════════════════════════════════════════════


def build_kg(rules_path: str | Path, enrich: bool = False) -> KGraph:
    """Pipeline: parsing deterministico → (opzionale) arricchimento LLM descrizioni."""
    categories = load_rules(rules_path)
    kg = parse_kg(categories)

    if enrich:
        kg = enrich_attribute_descriptions(kg)

    return kg
