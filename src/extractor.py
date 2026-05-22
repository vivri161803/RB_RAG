"""
src/extractor.py
----------------
Phase 3 — Rules Extractor.

Dato Level1 e Level2, estrae via Cypher tutti gli attributi applicabili
(macro-categoria + specifici sotto-categoria), deduplicati per nome.
"""

from __future__ import annotations

import logging

from neo4j import Driver

from src.models import AttributeNode

logger = logging.getLogger(__name__)


def extract_rules(driver: Driver, level1: str, level2: str) -> list[AttributeNode]:
    """Estrae gli attributi applicabili per la coppia Level1 + Level2.

    Recupera:
    - Attributi della macro-categoria (Level1) → campi comuni
    - Attributi della sotto-categoria (Level2) → campi specifici

    Deduplicazione per nome: se un attributo è sia L1 che L2, viene incluso una sola volta.
    Ordinamento: mandatory prima, poi optional.

    Args:
        driver: Driver Neo4j connesso.
        level1: Nome del Level1 (es. "Immobili").
        level2: Nome del Level2 (es. "Villa").

    Returns:
        Lista di AttributeNode deduplicati e ordinati.
    """
    records, _, _ = driver.execute_query(
        """
        MATCH (l1:Level1 {name: $l1})-[:REQUIRES]->(a:Attribute)
        RETURN a.name AS name, a.field_type AS field_type,
               a.description AS description, a.mandatory AS mandatory,
               "L1" AS source
        UNION
        MATCH (l2:Level2 {name: $l2})-[:REQUIRES]->(a:Attribute)
        RETURN a.name AS name, a.field_type AS field_type,
               a.description AS description, a.mandatory AS mandatory,
               "L2" AS source
        """,
        l1=level1,
        l2=level2,
    )

    # Deduplicazione per nome (L2 ha priorità se stesso attributo in entrambi)
    seen: dict[str, AttributeNode] = {}
    for r in records:
        name = r["name"]
        if name not in seen:
            seen[name] = AttributeNode(
                name=name,
                field_type=r["field_type"] or "str",
                description=r["description"] or "",
                mandatory=r["mandatory"] if r["mandatory"] is not None else False,
            )

    # Ordinamento: mandatory prima, poi per nome
    attributes = sorted(
        seen.values(),
        key=lambda a: (not a.mandatory, a.name),
    )

    logger.info(
        "Estratti %d attributi per %s → %s (%d mandatory, %d optional)",
        len(attributes),
        level1,
        level2,
        sum(1 for a in attributes if a.mandatory),
        sum(1 for a in attributes if not a.mandatory),
    )

    return attributes
