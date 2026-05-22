"""
src/main.py
-----------
CLI entrypoint per la pipeline Rules Retrieval.
Sottocomandi:
  - build-kg:  costruisce il Knowledge Graph da rules.json e lo carica su Neo4j.
  - route:     routing LLM + vector search per identificare Level1 e Level2.
  - extract:   estrae gli attributi applicabili via Cypher.
  - run:       pipeline completa: descrizione → JSON schema.
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


# ═══════════════════════════════════════════════════════════════
# Sottocomando: build-kg
# ═══════════════════════════════════════════════════════════════


def cmd_build_kg(args: argparse.Namespace) -> None:
    """Sottocomando build-kg: costruisce e carica il KG."""
    from src.config import get_neo4j_driver
    from src.kg.builder import build_kg
    from src.kg.embedder import populate_embeddings
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


# ═══════════════════════════════════════════════════════════════
# Sottocomando: route
# ═══════════════════════════════════════════════════════════════


def cmd_route(args: argparse.Namespace) -> None:
    """Sottocomando route: routing LLM → Level1 + Level2."""
    from src.config import get_neo4j_driver
    from src.routing import route

    logger = logging.getLogger("route")
    logger.info("═══ Routing: %s ═══", args.description[:60] + "...")

    driver = get_neo4j_driver()
    try:
        level1, level2, reason = route(driver, args.description)
    finally:
        driver.close()

    print()
    print("╔══════════════════════════════════════════╗")
    print("║           ROUTING COMPLETATO             ║")
    print("╠══════════════════════════════════════════╣")
    print(f"║  Level1:  {level1:<30} ║")
    print(f"║  Level2:  {level2:<30} ║")
    print("╠══════════════════════════════════════════╣")
    print(f"║  Reason:  {reason[:30]:<30} ║")
    print("╚══════════════════════════════════════════╝")


# ═══════════════════════════════════════════════════════════════
# Sottocomando: extract
# ═══════════════════════════════════════════════════════════════


def cmd_extract(args: argparse.Namespace) -> None:
    """Sottocomando extract: estrai regole via Cypher."""
    from src.config import get_neo4j_driver
    from src.extractor import extract_rules

    logger = logging.getLogger("extract")
    logger.info("═══ Estrazione: %s → %s ═══", args.level1, args.level2)

    driver = get_neo4j_driver()
    try:
        attributes = extract_rules(driver, args.level1, args.level2)
    finally:
        driver.close()

    # Output tabellare
    print()
    print(f"{'Nome':<45} {'Tipo':<8} {'Obbl.':<6} {'Descrizione'}")
    print("─" * 100)
    for attr in attributes:
        flag = "✓" if attr.mandatory else " "
        desc = (attr.description[:40] + "...") if len(attr.description) > 40 else attr.description
        print(f"{attr.name:<45} {attr.field_type:<8} {flag:<6} {desc}")

    print(f"\nTotale: {len(attributes)} attributi")


# ═══════════════════════════════════════════════════════════════
# Sottocomando: run (pipeline completa)
# ═══════════════════════════════════════════════════════════════


def cmd_run(args: argparse.Namespace) -> None:
    """Sottocomando run: pipeline completa → JSON schema."""
    from src.config import get_neo4j_driver
    from src.extractor import extract_rules
    from src.routing import route
    from src.schema_builder import build_schema, export_json_schema, save_json_schema

    logger = logging.getLogger("run")
    logger.info("═══ Pipeline completa ═══")

    driver = get_neo4j_driver()
    try:
        # Phase 2: Routing
        logger.info("── STEP 1/3: Routing ──")
        level1, level2, reason = route(driver, args.description)
        logger.info("Routing: %s → %s (%s)", level1, level2, reason[:50])

        # Phase 3: Extraction
        logger.info("── STEP 2/3: Estrazione regole ──")
        attributes = extract_rules(driver, level1, level2)

        # Phase 4: Schema Builder
        logger.info("── STEP 3/3: Generazione schema ──")
        model = build_schema(attributes)
        schema = export_json_schema(model)

        # Salva su file
        save_json_schema(schema, args.output)

    finally:
        driver.close()

    print()
    print("╔══════════════════════════════════════════╗")
    print("║       PIPELINE COMPLETATA                ║")
    print("╠══════════════════════════════════════════╣")
    print(f"║  Level1:      {level1:<26} ║")
    print(f"║  Level2:      {level2:<26} ║")
    print(f"║  Attributi:   {len(attributes):<26} ║")
    print(f"║  Output:      {str(args.output):<26} ║")
    print("╚══════════════════════════════════════════╝")


# ═══════════════════════════════════════════════════════════════
# CLI Parser
# ═══════════════════════════════════════════════════════════════


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
        "--input", default="rules/rules.json",
        help="Percorso al file rules.json (default: rules/rules.json)",
    )
    build_parser.add_argument(
        "--enrich", action="store_true",
        help="Usa l'LLM per generare descrizioni degli attributi",
    )
    build_parser.set_defaults(func=cmd_build_kg)

    # ── route ────────────────────────────────────────────────
    route_parser = subparsers.add_parser(
        "route",
        help="Routing: descrizione → Level1 + Level2",
    )
    route_parser.add_argument(
        "--description", required=True,
        help="Descrizione testuale del prodotto/asset",
    )
    route_parser.set_defaults(func=cmd_route)

    # ── extract ──────────────────────────────────────────────
    extract_parser = subparsers.add_parser(
        "extract",
        help="Estrazione regole: Level1 + Level2 → attributi",
    )
    extract_parser.add_argument(
        "--level1", required=True,
        help="Nome del Level1 (es. Immobili)",
    )
    extract_parser.add_argument(
        "--level2", required=True,
        help="Nome del Level2 (es. Villa)",
    )
    extract_parser.set_defaults(func=cmd_extract)

    # ── run (pipeline completa) ──────────────────────────────
    run_parser = subparsers.add_parser(
        "run",
        help="Pipeline completa: descrizione → JSON schema",
    )
    run_parser.add_argument(
        "--description", required=True,
        help="Descrizione testuale del prodotto/asset",
    )
    run_parser.add_argument(
        "--output", default="schema.json",
        help="Percorso del file di output JSON schema (default: schema.json)",
    )
    run_parser.set_defaults(func=cmd_run)

    # ── Parse e dispatch ─────────────────────────────────────
    args = parser.parse_args()
    setup_logging(args.log_level)
    args.func(args)


if __name__ == "__main__":
    main()
