# Requisiti — Phase 2-4: Router → Extractor → Schema Builder

## Scope

Implementare la pipeline completa da descrizione testuale a JSON schema:

1. **Phase 2 — Two-Stage Router**: data una descrizione testuale, identifica Level1 e Level2 tramite:
   - Step 1: LLM routing → Level1 + summary
   - Step 2: vector search cosine top-K tra Level2 del Level1 selezionato
   - Step 3: LLM reranking → Level2 finale

2. **Phase 3 — Rules Extractor**: dato Level1 + Level2, query Cypher per estrarre tutti gli attributi applicabili (macro + specifici), deduplicati.

3. **Phase 4 — Schema Builder**: dalla lista attributi, genera un modello Pydantic runtime con `create_model` e serializza il JSON schema su file.

## Decisioni Prese

| Decisione | Scelta |
|---|---|
| Modello LLM per routing/reranking | Stesso `LLM_MODEL` da `.env` |
| Output pipeline completa | JSON schema salvato su file (`--output schema.json`) |
| Provider ordering OpenRouter | `"sort": "throughput"` |
| Instructor mode | `JSON` (non tool calling — compatibilità cross-provider) |
| TOP_K per vector search | Configurabile da `.env` (default 5) |

## Contesto

- Neo4j è già popolato con il KG della Phase 1 (3 L1, 92 L2, 379 Attribute, 679 triple)
- I modelli Pydantic `RouterOutput` e `RerankerOutput` sono già definiti in `src/models.py`
- Gli embedding sono già presenti su ogni nodo Neo4j (`name_embedding` per L1/Attribute, `description_embedding` per L2)

## Out of Scope

- API REST / interfaccia web
- Caching delle risposte LLM
- Unit test automatici (solo verifica manuale per ora)
