"""
src/kg/neo4j_loader.py
----------------------
Caricamento del KGraph su Neo4j.
Gestisce pulizia, vincoli e scrittura tramite MERGE (idempotente).
"""

from __future__ import annotations

import logging

from neo4j import Driver

from src.models import KGraph

logger = logging.getLogger(__name__)


def clear_graph(driver: Driver) -> None:
    """Rimuove tutti i nodi e le relazioni dal database."""
    logger.info("Pulizia completa del grafo...")
    driver.execute_query("MATCH (n) DETACH DELETE n")
    logger.info("Grafo svuotato")


def create_constraints(driver: Driver) -> None:
    """Crea vincoli di unicità per evitare duplicati."""
    constraints = [
        (
            "constraint_level1_name",
            "CREATE CONSTRAINT constraint_level1_name IF NOT EXISTS "
            "FOR (n:Level1) REQUIRE n.name IS UNIQUE",
        ),
        (
            "constraint_level2_name",
            "CREATE CONSTRAINT constraint_level2_name IF NOT EXISTS "
            "FOR (n:Level2) REQUIRE n.name IS UNIQUE",
        ),
        (
            "constraint_attribute_name",
            "CREATE CONSTRAINT constraint_attribute_name IF NOT EXISTS "
            "FOR (n:Attribute) REQUIRE n.name IS UNIQUE",
        ),
    ]
    for name, query in constraints:
        logger.debug("Creazione vincolo: %s", name)
        driver.execute_query(query)

    logger.info("Vincoli di unicità creati/verificati")


def load_graph(driver: Driver, kg: KGraph) -> dict[str, int]:
    """Carica il KGraph completo su Neo4j.

    Restituisce un dizionario con i conteggi di nodi e archi creati.
    """
    counts = {
        "level1_nodes": 0,
        "level2_nodes": 0,
        "attribute_nodes": 0,
        "belongs_to_rels": 0,
        "requires_rels": 0,
    }

    # ── Nodi Level1 ──────────────────────────────────────────
    for node in kg.level1_nodes:
        driver.execute_query(
            """
            MERGE (n:Level1 {name: $name})
            SET n.description = $description,
                n.name_embedding = $name_embedding
            """,
            name=node.name,
            description=node.description,
            name_embedding=node.name_embedding,
        )
        counts["level1_nodes"] += 1

    logger.info("Caricati %d nodi Level1", counts["level1_nodes"])

    # ── Nodi Level2 ──────────────────────────────────────────
    for node in kg.level2_nodes:
        driver.execute_query(
            """
            MERGE (n:Level2 {name: $name})
            SET n.description = $description,
                n.description_embedding = $description_embedding
            """,
            name=node.name,
            description=node.description,
            description_embedding=node.description_embedding,
        )
        counts["level2_nodes"] += 1

    logger.info("Caricati %d nodi Level2", counts["level2_nodes"])

    # ── Nodi Attribute ───────────────────────────────────────
    for node in kg.attributes:
        driver.execute_query(
            """
            MERGE (n:Attribute {name: $name})
            SET n.field_type = $field_type,
                n.description = $description,
                n.mandatory = $mandatory,
                n.name_embedding = $name_embedding
            """,
            name=node.name,
            field_type=node.field_type,
            description=node.description,
            mandatory=node.mandatory,
            name_embedding=node.name_embedding,
        )
        counts["attribute_nodes"] += 1

    logger.info("Caricati %d nodi Attribute", counts["attribute_nodes"])

    # ── Archi BELONGS_TO ─────────────────────────────────────
    for triple in kg.triples_belongs_to:
        driver.execute_query(
            """
            MATCH (l2:Level2 {name: $l2_name})
            MATCH (l1:Level1 {name: $l1_name})
            MERGE (l2)-[:BELONGS_TO]->(l1)
            """,
            l2_name=triple.source,
            l1_name=triple.target,
        )
        counts["belongs_to_rels"] += 1

    logger.info("Caricati %d archi BELONGS_TO", counts["belongs_to_rels"])

    # ── Archi REQUIRES (L1 → Attribute) ─────────────────────
    for triple in kg.triples_requires_l1:
        driver.execute_query(
            """
            MATCH (l1:Level1 {name: $l1_name})
            MATCH (a:Attribute {name: $attr_name})
            MERGE (l1)-[:REQUIRES]->(a)
            """,
            l1_name=triple.source,
            attr_name=triple.target,
        )
        counts["requires_rels"] += 1

    # ── Archi REQUIRES (L2 → Attribute) ─────────────────────
    for triple in kg.triples_requires_l2:
        driver.execute_query(
            """
            MATCH (l2:Level2 {name: $l2_name})
            MATCH (a:Attribute {name: $attr_name})
            MERGE (l2)-[:REQUIRES]->(a)
            """,
            l2_name=triple.source,
            attr_name=triple.target,
        )
        counts["requires_rels"] += 1

    logger.info("Caricati %d archi REQUIRES totali", counts["requires_rels"])

    return counts
