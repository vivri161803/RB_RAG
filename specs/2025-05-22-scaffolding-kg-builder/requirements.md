# Requirements — Phase 0 (Scaffolding) + Phase 1 (KG Builder)

## Scope

Implementare le fondamenta del progetto (configurazione, modelli, struttura directory) e la pipeline completa di costruzione del Knowledge Graph a partire da `rules/rules.json`, con caricamento su Neo4j.

---

## Decisioni Prese

1. **LLM-based triple extraction**: l'LLM estrae entità e relazioni dal JSON tramite Instructor + Pydantic, NON parsing manuale.
2. **3 chiamate LLM totali**: una per macro-categoria (Immobili, Aziende, Attività Commerciali). Ogni prompt include tutto il contenuto della categoria + le sue sotto-categorie.
3. **Branch**: lavoro sul branch corrente (no feature branch).
4. **Provider**: OpenRouter con ordinamento per throughput; modello LLM da `.env` (`LLM_MODEL`), embedding da `.env` (`EMBEDDING_MODEL`).
5. **Settings**: Pydantic `BaseSettings` con `pydantic-settings` per caricare `.env`.
6. **Level2 embedding**: `description_embedding` (non `name_embedding`).

---

## Contesto Tecnico

### .env corrente
```
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=***
API=sk-or-v1-***
LLM_MODEL=openai/gpt-oss-20b
EMBEDDING_MODEL=openai/text-embedding-3-small
TOP_K=5
```

### Schema KG (Neo4j)

**Nodi:**
- `Level1`: `id`, `description`, `name_embedding: float[]`
- `Level2`: `id`, `description`, `description_embedding: float[]`
- `Attribute`: `name`, `field_type`, `description`, `name_embedding: float[]`, `mandatory: bool`

**Relazioni:**
- `(Level2)-[:BELONGS_TO]->(Level1)` — esclusività
- `(Level1)-[:REQUIRES]->(Attribute)` — campi macro-categoria
- `(Level2)-[:REQUIRES]->(Attribute)` — campi specifici sotto-categoria

### Instructor Pattern
```python
import instructor
from openai import OpenAI

client = instructor.from_openai(
    OpenAI(base_url="https://openrouter.ai/api/v1", api_key=settings.API),
)
result = client.create(
    model=settings.LLM_MODEL,
    response_model=KGChunk,
    messages=[...],
)
```

### Neo4j Pattern
```python
from neo4j import GraphDatabase

with GraphDatabase.driver(URI, auth=AUTH) as driver:
    driver.execute_query("MERGE (n:Level1 {id: $id}) SET n.description = $desc", ...)
```
