# Requisiti — Phase 5: Backend API (FastAPI)

## Scope

Esporre la pipeline Rules Retrieval come servizio HTTP REST tramite **FastAPI**, containerizzato con **Docker Compose** (app + Neo4j).

L'API è ad **uso interno** — nessuna autenticazione richiesta.

## Decisioni Prese

| Decisione | Scelta | Motivazione |
|---|---|---|
| Framework | **FastAPI** (Python) | Coerente con il resto del progetto, typing nativo Pydantic |
| Autenticazione | Nessuna | Uso interno, rete privata |
| Containerizzazione | Docker Compose | Neo4j + FastAPI in un unico stack |
| Documentazione API | OpenAPI auto-generata da FastAPI | Zero effort, sempre aggiornata |
| Async/Sync | **Sync** (endpoints) | Le chiamate a Neo4j e OpenRouter sono sync; FastAPI usa threadpool automaticamente |

## Contesto

La logica core è già implementata e testata:

- `src/routing/` — Pipeline routing (LLM → vector search → reranking)
- `src/extractor.py` — Estrazione regole via Cypher
- `src/schema_builder.py` — Generazione JSON Schema
- `src/kg/builder.py` — Costruzione KG (parsing deterministico)
- `src/kg/embedder.py` — Embedding via OpenRouter
- `src/kg/neo4j_loader.py` — Caricamento su Neo4j

Il backend è un **thin wrapper HTTP** sopra queste funzioni.

## Endpoint

| Metodo | Path | Descrizione |
|---|---|---|
| `POST` | `/route` | Routing: descrizione → Level1 + Level2 |
| `POST` | `/extract` | Estrazione: Level1 + Level2 → attributi |
| `POST` | `/run` | Pipeline completa: descrizione → JSON Schema (da esporre) |
| `POST` | `/build-kg` | Trigger rebuild del Knowledge Graph |
| `GET` | `/health` | Health check: stato servizio + Neo4j |

## Request/Response Models

### `POST /route`

```json
// Request
{"description": "Villa con piscina in Toscana, 500 mq, 10 camere"}

// Response 200
{
  "level1": "Immobili",
  "level2": "Villa",
  "reason": "La descrizione indica una proprietà residenziale..."
}
```

### `POST /extract`

```json
// Request
{"level1": "Immobili", "level2": "Villa"}

// Response 200
{
  "level1": "Immobili",
  "level2": "Villa",
  "attributes": [
    {"name": "Regione", "field_type": "str", "description": "...", "mandatory": true},
    ...
  ],
  "count": 22
}
```

### `POST /run`

```json
// Request
{"description": "Villa con piscina in Toscana, 500 mq"}

// Response 200
{
  "level1": "Immobili",
  "level2": "Villa",
  "reason": "...",
  "attributes_count": 22,
  "schema": { ... JSON Schema completo ... }
}
```

### `POST /build-kg`

```json
// Request
{"enrich": false}

// Response 200
{
  "status": "completed",
  "counts": {
    "level1_nodes": 3,
    "level2_nodes": 92,
    "attribute_nodes": 379,
    "belongs_to_rels": 92,
    "requires_rels": 587
  }
}
```

### `GET /health`

```json
// Response 200
{
  "status": "healthy",
  "neo4j": "connected",
  "timestamp": "2025-05-22T17:00:00Z"
}

// Response 503
{
  "status": "unhealthy",
  "neo4j": "disconnected",
  "error": "ServiceUnavailable: Unable to connect to bolt://localhost:7687"
}
```

## Error Handling

Formato errore standardizzato:

```json
{
  "error": "Neo4jConnectionError",
  "detail": "Impossibile connettersi a Neo4j: bolt://localhost:7687",
  "status_code": 503
}
```

| Caso | HTTP Status |
|---|---|
| Validazione input fallita | `422 Unprocessable Entity` (gestito da FastAPI/Pydantic) |
| Neo4j non raggiungibile | `503 Service Unavailable` |
| OpenRouter timeout/errore | `502 Bad Gateway` |
| Errore generico | `500 Internal Server Error` |

## Out of Scope (v1)

- Autenticazione / autorizzazione
- Rate limiting
- Caching delle risposte
- WebSocket / streaming
- Metriche Prometheus
- CI/CD pipeline
