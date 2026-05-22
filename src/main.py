"""
src/main.py
-----------
CLI entrypoint per la pipeline Rules Retrieval.
Sottocomandi:
  - build-kg: costruisce il Knowledge Graph da rules.json e lo carica su Neo4j.
"""

from __future__ import annotations

import argparse
import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """Configura il logging strutturato."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
        datefmt="%H:%M:%S",
    )


def cmd_build_kg(args: argparse.Namespace) -> None:
    """Sottocomando build-kg: costruisce e carica il KG."""
    from src.config import get_neo4j_driver
    from src.kg.builder import build_kg
    from src.kg.embedder import deduplicate_attributes, populate_embeddings
    from src.kg.neo4j_loader import clear_graph, create_constraints, load_graph

    logger = logging.getLogger("build-kg")

    # 1. Parsing deterministico + (opzionale) arricchimento LLM descrizioni
    logger.info("═══ STEP 1/3: Parsing deterministico da %s ═══", args.input)
    kg = build_kg(args.input, enrich=args.enrich)

    # 2. Generazione embedding via OpenRouter
    logger.info("═══ STEP 2/3: Generazione embedding ═══")
    kg = populate_embeddings(kg)

    # 3. Caricamento su Neo4j
    logger.info("═══ STEP 3/3: Caricamento su Neo4j ═══")
    driver = get_neo4j_driver()
    try:
        clear_graph(driver)
        create_constraints(driver)
        counts = load_graph(driver, kg)
    finally:
        driver.close()

    # Riepilogo
    print()
    print("╔══════════════════════════════════════════╗")
    print("║         KG BUILD COMPLETATO              ║")
    print("╠══════════════════════════════════════════╣")
    print(f"║  Level1 nodes:    {counts['level1_nodes']:>5}                  ║")
    print(f"║  Level2 nodes:    {counts['level2_nodes']:>5}                  ║")
    print(f"║  Attribute nodes: {counts['attribute_nodes']:>5}                  ║")
    print(f"║  BELONGS_TO rels: {counts['belongs_to_rels']:>5}                  ║")
    print(f"║  REQUIRES rels:   {counts['requires_rels']:>5}                  ║")
    print("╚══════════════════════════════════════════╝")


def main() -> None:
    """Punto d'ingresso CLI."""
    parser = argparse.ArgumentParser(
        prog="rules-retrieval",
        description="Rules Retrieval Pipeline — Domain Rule-Based RAG via KG",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Livello di logging (default: INFO)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # ── build-kg ─────────────────────────────────────────────
    build_parser = subparsers.add_parser(
        "build-kg",
        help="Costruisce il Knowledge Graph da rules.json e lo carica su Neo4j",
    )
    build_parser.add_argument(
        "--input",
        default="rules/rules.json",
        help="Percorso al file rules.json (default: rules/rules.json)",
    )
    build_parser.add_argument(
        "--enrich",
        action="store_true",
        help="Usa l'LLM per generare descrizioni degli attributi (opzionale)",
    )
    build_parser.set_defaults(func=cmd_build_kg)

    # ── Parse e dispatch ─────────────────────────────────────
    args = parser.parse_args()
    setup_logging(args.log_level)
    args.func(args)


if __name__ == "__main__":
    main()
