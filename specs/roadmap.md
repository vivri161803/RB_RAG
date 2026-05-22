# Roadmap — Rules Retrieval Pipeline

## Overview delle Fasi

```
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4
Scaffolding  KG Build  Routing   Extract   Schema
```

---

## Phase 0 — Scaffolding & Configurazione

**Obiettivo:** struttura di progetto funzionante, dipendenze installate, config caricata.

### Tasks

- [ ] Aggiungere dipendenze a `pyproject.toml` (`pydantic`, `instructor`, `openai`, `neo4j`, `numpy`, `python-dotenv`) tramite `uv add`
- [ ] Creare struttura directory `src/` con `__init__.py` in ogni package
- [ ] Implementare `src/config.py`:
  - Legge `.env` con `python-dotenv`
  - Espone `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `API`, `MODEL`, `EMBEDDING_MODEL`, `TOP_K`
  - Valida la presenza delle chiavi obbligatorie (Pydantic `BaseSettings`)
- [ ] Implementare `src/models.py` con i Pydantic model condivisi:
  - `Level1Node` (nome, descrizione), `Level2Node` (nome, descrizione, ambedding descrizione), `AttributeNode` (nome, tipo del campo, descrizione, obbligatorio [booleano])
  - `RouterOutput` (livello 1 + riassunto ≤100 parole)
  - `RerankerOutput` (livello 2 scelto)


**Verifica:** `uv run python -c "from src.config import settings; print(settings)"` senza errori.

---

## Phase 1 — Knowledge Graph Builder (FASE 1 del progetto)

**Obiettivo:** leggere `rules/rules.json`, generare embedding, costruire il grafo e caricarlo su Neo4j.

### Tasks

- [ ] `src/kg/builder.py` — estrazione LLM delle triple dal JSON:
  - Per ogni categoria in `rules.json`, costruire un prompt che include il testo della categoria (id, description, mandatory_fields, optional_fields, sub_categories)
  - Chiamare l'LLM via `instructor` con output strutturato `KGChunk` (Pydantic BaseModel):
    ```python
    class KGChunk(BaseModel):
        level1: Level1Node
        level2_list: list[Level2Node]
        attributes: list[AttributeNode]
        triples_belongs_to: list[tuple[str, str]]   # (level2_id, level1_id)
        triples_requires_l1: list[tuple[str, str]]   # (level1_id, attr_name)
        triples_requires_l2: list[tuple[str, str]]   # (level2_id, attr_name)
    ```
  - L'LLM legge la categoria ed estrae autonomamente entità e relazioni seguendo lo schema ontologico
  - Aggregare i `KGChunk` di tutte le categorie in un unico `KGraph(BaseModel)` con deduplicazione degli attributi
- [ ] `src/kg/embedder.py` — generazione embedding post-estrazione:
  - Funzione `embed_text(text: str) -> list[float]` via OpenRouter embedding
  - Funzione `cosine_similarity(a, b) -> float` con numpy
  - Popolare il campo `description_embedding` di ogni `Level1Node`, `Level2Node`, `AttributeNode` dopo l'estrazione LLM
  - Deduplicare `AttributeNode` con nome simile (cosine sim > 0.95) prima del caricamento
- [ ] `src/kg/neo4j_loader.py` — caricamento su Neo4j:
  - `clear_graph()` — DROP completo prima del rebuild
  - `create_constraints()` — unicità su `Level1.id`, `Level2.id`, `Attribute.name`
  - `load_graph(kg: KGraph)` — singola funzione che itera le triple del `KGraph` e le scrive:
    - Nodi `Level1`, `Level2`, `Attribute` con `MERGE`
    - Archi `BELONGS_TO`, `REQUIRES` con `MERGE`
  - Uso di `MERGE` Cypher per idempotenza (per evitare duplicati)
- [ ] `src/main.py` — sottocomando `build-kg`:

  ```
  uv run python -m src.main build-kg --input rules/rules.json
  ```

**Verifica:** Neo4j Browser mostra nodi Level1 (3), Level2 (~90), Attribute (~200+) con relazioni corrette.

---

## Phase 2 — Two-Stage Router (FASE 2 del progetto)

**Obiettivo:** data una descrizione testuale, identificare livello 1 e livello 2 via LLM + vector search + reranking.

### Tasks

- [ ] `src/routing/llm_router.py` — Step 1 LLM routing:
  - Prompt che mostra i 3 Level1 con le loro `description`
  - Output strutturato Pydantic `RouterOutput` via `instructor`
  - Provider OpenRouter ordinato per throughput (`provider.order`)
- [ ] `src/routing/vector_search.py` — Step 2 top-K cosine search:
  - Recupera da Neo4j tutti i `Level2` appartenenti al `Level1` individuato (con i loro `description_embedding`)
  - Calcola cosine similarity tra embedding del `riassunto` (da `RouterOutput`) e ogni `description_embedding`
  - Restituisce i top-K=5 `Level2` ordinati per similarità del coseno
- [ ] `src/routing/reranker.py` — Step 3 LLM reranking:
  - Prompt con i top-K Level2 (id + description) e il riassunto del prodotto
  - Output strutturato `RerankerOutput` via `instructor`
- [ ] `src/main.py` — sottocomando `route`:
  ```
  uv run python -m src.main route --description "Villa con piscina in Toscana..."
  ```
  Output: `level1`, `level2`

**Verifica:** test manuale con 5 descrizioni di prodotti diversi → routing corretto in ≥4/5 casi.

---

## Phase 3 — Rules Extractor (FASE 3 del progetto)

**Obiettivo:** dato livello 1 e livello 2, estrarre via Cypher tutti gli attributi applicabili.

### Tasks

- [ ] `src/extractor.py`:
  - Query Cypher che recupera attributi di Level1 + attributi specifici di Level2
  - Deduplicazione attributi in caso di overlap (per nome)
  - Restituisce lista di `AttributeNode` con `name`, `field_type`, `description`, `mandatory`
- [ ] `src/main.py` — sottocomando `extract`:
  ```
  uv run python -m src.main extract --level1 Immobili --level2 Villa
  ```
  Output: lista attributi in formato tabellare o JSON

**Verifica:** `extract --level1 Immobili --level2 Villa` restituisce attributi macro + specifici villa, nessun duplicato.

---

## Phase 4 — Schema Builder (FASE 4 del progetto)

**Obiettivo:** generare uno schema Pydantic runtime dalla lista attributi e serializzarlo come JSON.

### Tasks

- [ ] `src/schema_builder.py`:
  - `build_schema(attributes: list[AttributeNode]) -> type[BaseModel]`
  - Mappa `field_type` (stringa libera dal KG) → tipo Python (`str`, `int`, `float`, `bool`)
  - Usa `pydantic.create_model` per costruire il modello dinamicamente
  - Campi `mandatory=True` → campo obbligatorio (senza default)
  - Campi `mandatory=False` → `Optional[T] = None`
  - `export_json_schema(model) -> dict` — serializza con `model.model_json_schema()`
- [ ] `src/main.py` — sottocomando `run` (pipeline completa):
  ```
  uv run python -m src.main run --description "..." [--output schema.json]
  ```
  Esegue FASE 2 → 3 → 4 in sequenza e salva il JSON schema

**Verifica:** JSON schema valido per 3 prodotti campione (uno per macro-categoria).

---

## Phase 5 — Integrazione & Qualità

**Obiettivo:** hardening, logging, gestione errori, documentazione CLI.

### Tasks

- [ ] Aggiungere logging strutturato (`logging` stdlib) con livello configurabile via `LOG_LEVEL` in `.env`
- [ ] Gestione graceful degli errori Neo4j (connessione assente → messaggio chiaro)
- [ ] Gestione rate limit OpenRouter (retry esponenziale)
- [ ] Aggiornare `README.md` con:
  - Setup rapido (Neo4j, `.env`, `uv sync`)
  - Comandi CLI con esempi
  - Schema del KG
- [ ] Test end-to-end: descrizione prodotto → schema JSON per tutti e 3 i livelli 1

---

## Ordine di Esecuzione Raccomandato

```
Phase 0 (1-2h) → Phase 1 (3-4h) → Phase 2 (3-4h) → Phase 3 (1h) → Phase 4 (2h) → Phase 5 (1-2h)
```

Tempo totale stimato: **~12-14 ore** di sviluppo.
