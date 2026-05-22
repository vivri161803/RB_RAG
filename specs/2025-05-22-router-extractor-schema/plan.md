# Piano di Implementazione — Phase 2-4

## Gruppo 1 — Phase 2: Two-Stage Router

### 1.1 `src/routing/llm_router.py` — Step 1 LLM routing

- Funzione `route_level1(description: str) -> RouterOutput`
- Recupera da Neo4j i 3 nodi Level1 con `name` e `description`
- Costruisce prompt di sistema con le 3 categorie disponibili
- Chiama LLM via Instructor (JSON mode) con modello `RouterOutput`
- Provider ordering: `"sort": "throughput"`

### 1.2 `src/routing/vector_search.py` — Step 2 vector search

- Funzione `search_level2_candidates(level1_name: str, summary: str, top_k: int) -> list[tuple[str, float]]`
- Recupera da Neo4j tutti i Level2 BELONGS_TO il Level1 selezionato, con i loro `description_embedding`
- Genera embedding del `summary` (dal `RouterOutput`) tramite `embedder.embed_text()`
- Calcola cosine similarity (`numpy`) tra embedding summary e ogni `description_embedding`
- Restituisce top-K Level2 ordinati per similarity decrescente (lista di `(level2_name, score)`)

### 1.3 `src/routing/reranker.py` — Step 3 LLM reranking

- Funzione `rerank_level2(description: str, candidates: list[tuple[str, str]]) -> RerankerOutput`
- `candidates` = lista di `(level2_name, level2_description)` dei top-K
- Prompt con la descrizione originale + i candidati numerati
- Chiama LLM via Instructor (JSON mode) con modello `RerankerOutput`

### 1.4 `src/routing/__init__.py` — Pipeline routing

- Funzione `route(description: str) -> tuple[str, str, str]`
- Orchestrazione: `route_level1` → `search_level2_candidates` → `rerank_level2`
- Restituisce `(level1_name, level2_name, reason)`

### 1.5 `src/main.py` — Sottocomando `route`

- Aggiungere subparser `route` con flag `--description "..."`
- Output a console: Level1, Level2, reason

---

## Gruppo 2 — Phase 3: Rules Extractor

### 2.1 `src/extractor.py`

- Funzione `extract_rules(driver, level1: str, level2: str) -> list[AttributeNode]`
- Query Cypher:
  ```cypher
  MATCH (l1:Level1 {name: $l1})-[:REQUIRES]->(a:Attribute)
  RETURN a.name, a.field_type, a.description, a.mandatory, "L1" AS source
  UNION
  MATCH (l2:Level2 {name: $l2})-[:REQUIRES]->(a:Attribute)
  RETURN a.name, a.field_type, a.description, a.mandatory, "L2" AS source
  ```
- Deduplicazione per nome (attributi L1 e L2 possono sovrapporsi)
- Restituisce lista `AttributeNode` ordinata: mandatory prima, poi optional

### 2.2 `src/main.py` — Sottocomando `extract`

- Aggiungere subparser `extract` con `--level1` e `--level2`
- Output: tabella formattata o JSON degli attributi

---

## Gruppo 3 — Phase 4: Schema Builder

### 3.1 `src/schema_builder.py`

- Funzione `build_schema(attributes: list[AttributeNode]) -> type[BaseModel]`
  - Mappa `field_type` → tipo Python:
    - `"str"` → `str`
    - `"int"` → `int`
    - `"float"` → `float`
    - `"bool"` → `bool`
  - `mandatory=True` → campo obbligatorio (`...`)
  - `mandatory=False` → `Optional[T] = None`
  - Usa `pydantic.create_model("ProductSchema", **fields)`
- Funzione `export_json_schema(model) -> dict`
  - Chiama `model.model_json_schema()`
  - Restituisce il dict schema

### 3.2 `src/main.py` — Sottocomando `run` (pipeline completa)

- Aggiungere subparser `run` con `--description "..."` e `--output schema.json`
- Esegue in sequenza: route → extract → build_schema → export
- Salva il JSON schema su file

---

## Ordine di Implementazione

1. **Gruppo 1** (Router) — dipende da Neo4j popolato ✅
2. **Gruppo 2** (Extractor) — dipende da Neo4j popolato ✅
3. **Gruppo 3** (Schema Builder) — dipende da Extractor
4. **CLI** — aggiornamento `main.py` con tutti i sottocomandi
