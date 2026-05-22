# Plan — Phase 0 (Scaffolding) + Phase 1 (KG Builder)

## Group 1 — Dipendenze e struttura directory

1.1. `uv add pydantic pydantic-settings instructor openai neo4j numpy python-dotenv`
1.2. Creare directory `src/`, `src/kg/`, `src/routing/` con `__init__.py`
1.3. Aggiornare `.env` se necessario (i campi `LLM_MODEL`, `EMBEDDING_MODEL`, `TOP_K` sono già presenti)

---

## Group 2 — Configurazione (`src/config.py`)

2.1. Implementare `Settings(BaseSettings)` con:
  - `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`
  - `API` (chiave OpenRouter)
  - `LLM_MODEL`, `EMBEDDING_MODEL`
  - `TOP_K: int = 5`
  - `model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')`
2.2. Singleton `settings = Settings()`
2.3. Helper `get_openai_client()` → `OpenAI(base_url="https://openrouter.ai/api/v1", api_key=settings.API)`
2.4. Helper `get_instructor_client()` → `instructor.from_openai(get_openai_client())`
2.5. Helper `get_neo4j_driver()` → `GraphDatabase.driver(settings.NEO4J_URI, auth=(...))`

---

## Group 3 — Modelli Pydantic (`src/models.py`)

3.1. `Level1Node(BaseModel)`: `id: str`, `description: str`, `name_embedding: list[float] = []`
3.2. `Level2Node(BaseModel)`: `id: str`, `description: str`, `description_embedding: list[float] = []`
3.3. `AttributeNode(BaseModel)`: `name: str`, `field_type: str = "str"`, `description: str = ""`, `mandatory: bool`, `name_embedding: list[float] = []`
3.4. `KGChunk(BaseModel)`: `level1: Level1Node`, `level2_list: list[Level2Node]`, `attributes: list[AttributeNode]`, `triples_belongs_to: list[tuple[str, str]]`, `triples_requires_l1: list[tuple[str, str]]`, `triples_requires_l2: list[tuple[str, str]]`
3.5. `KGraph(BaseModel)`: `level1_nodes: list[Level1Node]`, `level2_nodes: list[Level2Node]`, `attributes: list[AttributeNode]`, `triples_belongs_to: list[tuple[str, str]]`, `triples_requires_l1: list[tuple[str, str]]`, `triples_requires_l2: list[tuple[str, str]]`
  - Metodo `merge_chunk(chunk: KGChunk)` per aggregare chunk mantenendo unicità degli attributi per nome
3.6. `RouterOutput(BaseModel)`: `level1_id: str`, `summary: str` (max 100 parole — per Phase 2, definita ora)
3.7. `RerankerOutput(BaseModel)`: `level2_id: str`, `reason: str` (per Phase 2, definita ora)

---

## Group 4 — KG Builder (`src/kg/builder.py`)

4.1. Funzione `load_rules(path: str) -> list[dict]`: carica `rules.json` e restituisce la lista `categories`
4.2. Funzione `build_extraction_prompt(category: dict) -> str`: costruisce il prompt che include tutto il JSON della categoria (id, description, mandatory_fields, optional_fields, sub_categories completo)
4.3. Funzione `extract_kg_chunk(category: dict) -> KGChunk`:
  - Chiama l'LLM via `instructor` con `response_model=KGChunk`
  - Prompt di sistema: spiega lo schema ontologico (Level1, Level2, Attribute, BELONGS_TO, REQUIRES)
  - Prompt utente: il JSON della categoria
  - Provider ordering: `extra_body={"provider": {"order": ["Throughput"]}}`
4.4. Funzione `build_kg(rules_path: str) -> KGraph`:
  - Per ogni categoria: `extract_kg_chunk(cat)` → `kg.merge_chunk(chunk)`
  - Restituisce il `KGraph` aggregato

---

## Group 5 — Embedder (`src/kg/embedder.py`)

5.1. Funzione `embed_text(text: str) -> list[float]`: chiama OpenRouter embedding API con `EMBEDDING_MODEL`
5.2. Funzione `embed_batch(texts: list[str]) -> list[list[float]]`: batch di embedding per efficienza
5.3. Funzione `cosine_similarity(a: list[float], b: list[float]) -> float`: calcolo con numpy
5.4. Funzione `populate_embeddings(kg: KGraph) -> KGraph`:
  - Per ogni `Level1Node`: `name_embedding = embed_text(node.id)`
  - Per ogni `Level2Node`: `description_embedding = embed_text(node.description)`
  - Per ogni `AttributeNode`: `name_embedding = embed_text(node.name)`
5.5. Funzione `deduplicate_attributes(kg: KGraph, threshold: float = 0.95) -> KGraph`:
  - Confronta `name_embedding` di tutti gli `AttributeNode`
  - Se cosine sim > threshold: merge (tiene il primo, aggiorna le triple)

---

## Group 6 — Neo4j Loader (`src/kg/neo4j_loader.py`)

6.1. Funzione `clear_graph(driver)`: `MATCH (n) DETACH DELETE n`
6.2. Funzione `create_constraints(driver)`:
  - `CREATE CONSTRAINT IF NOT EXISTS FOR (n:Level1) REQUIRE n.id IS UNIQUE`
  - `CREATE CONSTRAINT IF NOT EXISTS FOR (n:Level2) REQUIRE n.id IS UNIQUE`
  - `CREATE CONSTRAINT IF NOT EXISTS FOR (n:Attribute) REQUIRE n.name IS UNIQUE`
6.3. Funzione `load_graph(driver, kg: KGraph)`:
  - MERGE nodi Level1 con proprietà (id, description, name_embedding)
  - MERGE nodi Level2 con proprietà (id, description, description_embedding)
  - MERGE nodi Attribute con proprietà (name, field_type, description, name_embedding, mandatory)
  - MERGE archi BELONGS_TO da triple
  - MERGE archi REQUIRES da triple L1 e L2

---

## Group 7 — CLI Entrypoint (`src/main.py`)

7.1. Sottocomando `build-kg`:
  - Argomento `--input` (default: `rules/rules.json`)
  - Flusso: `load_rules → build_kg → populate_embeddings → deduplicate_attributes → load_graph`
  - Stampa riepilogo finale (conteggi nodi e archi)
7.2. Usare `argparse` per il parsing argomenti CLI

---

## Group 8 — Verifica

8.1. `uv run python -c "from src.config import settings; print(settings)"` → no errori
8.2. `uv run python -m src.main build-kg --input rules/rules.json` → KG caricato su Neo4j
8.3. Verifica in Neo4j Browser: 3 nodi Level1, ~90 nodi Level2, ~200+ nodi Attribute
