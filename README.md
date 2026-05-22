## KG Build

uv run python -m src.main build-kg --input rules/rules.json 

379 attributes
3 level1
92 level2

RESULT LLM: 

╔══════════════════════════════════════════╗
║         KG BUILD COMPLETATO              ║
╠══════════════════════════════════════════╣
║  Level1 nodes:        3                  ║
║  Level2 nodes:       92                  ║
║  Attribute nodes:   325                  ║
║  BELONGS_TO rels:    92                  ║
║  REQUIRES rels:     579                  ║
╚══════════════════════════════════════════╝

-----
uv run python -m src.main build-kg --input rules/rules.json --enrich

╔══════════════════════════════════════════╗
║         KG BUILD COMPLETATO              ║
╠══════════════════════════════════════════╣
║  Level1 nodes:        3                  ║
║  Level2 nodes:       92                  ║
║  Attribute nodes:   379                  ║
║  BELONGS_TO rels:    92                  ║
║  REQUIRES rels:     587                  ║
╚══════════════════════════════════════════╝