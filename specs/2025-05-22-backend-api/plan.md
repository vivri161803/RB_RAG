# Piano di Implementazione — Phase 5: Backend API (FastAPI)

## Gruppo 1 — Struttura e dipendenze

### 1.1 Dipendenze

```bash
uv add fastapi uvicorn[standard]
```

### 1.2 `src/api/models.py` — Request/Response Pydantic models

Modelli dedicati all'API (separati dai modelli KG):

- `RouteRequest(description: str)`
- `RouteResponse(level1: str, level2: str, reason: str)`
- `ExtractRequest(level1: str, level2: str)`
- `ExtractResponse(level1: str, level2: str, attributes: list[AttributeOut], count: int)`
- `RunRequest(description: str)`
- `RunResponse(level1: str, level2: str, reason: str, attributes_count: int, schema: dict)`
- `BuildKGRequest(enrich: bool = False)`
- `BuildKGResponse(status: str, counts: dict)`
- `HealthResponse(status: str, neo4j: str, timestamp: str)`
- `ErrorResponse(error: str, detail: str, status_code: int)`
- `AttributeOut(name: str, field_type: str, description: str, mandatory: bool)` — senza embedding

### 1.3 `src/api/__init__.py`

Package init vuoto.

---

## Gruppo 2 — Endpoint e App FastAPI

### 2.1 `src/api/deps.py` — Dependency injection

- `get_driver() -> Driver` — Dependency FastAPI che fornisce il driver Neo4j
  - Usa `src.config.get_neo4j_driver()` con lifecycle gestito dall'app
  - Il driver viene creato al startup e chiuso allo shutdown (`lifespan`)
- Gestione errore connessione: se Neo4j non è raggiungibile, risponde `503`

### 2.2 `src/api/app.py` — FastAPI application

- `lifespan` context manager per startup/shutdown del driver Neo4j
- CORS middleware con `allow_origins=["*"]` (uso interno)
- Exception handlers globali:
  - `neo4j.exceptions.ServiceUnavailable` → `503`
  - `openai.APIError` → `502`
  - `Exception` → `500`
- Include router da `src/api/routes.py`

### 2.3 `src/api/routes.py` — Endpoint definitions

Ogni endpoint è un thin wrapper:

#### `POST /route`
```python
@router.post("/route", response_model=RouteResponse)
def route_endpoint(req: RouteRequest, driver = Depends(get_driver)):
    level1, level2, reason = route(driver, req.description)
    return RouteResponse(level1=level1, level2=level2, reason=reason)
```

#### `POST /extract`
```python
@router.post("/extract", response_model=ExtractResponse)
def extract_endpoint(req: ExtractRequest, driver = Depends(get_driver)):
    attributes = extract_rules(driver, req.level1, req.level2)
    return ExtractResponse(...)
```

#### `POST /run`
```python
@router.post("/run", response_model=RunResponse)
def run_endpoint(req: RunRequest, driver = Depends(get_driver)):
    # route → extract → build_schema → export
    ...
```

#### `POST /build-kg`
```python
@router.post("/build-kg", response_model=BuildKGResponse)
def build_kg_endpoint(req: BuildKGRequest, driver = Depends(get_driver)):
    # build_kg → embeddings → clear/load Neo4j
    ...
```

#### `GET /health`
```python
@router.get("/health", response_model=HealthResponse)
def health_endpoint(driver = Depends(get_driver)):
    # Test connessione Neo4j con query leggera
    ...
```

---

## Gruppo 3 — Docker Compose

### 3.1 `Dockerfile`

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen
COPY . .
CMD ["uv", "run", "uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3.2 `docker-compose.yml`

```yaml
services:
  neo4j:
    image: neo4j:latest
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}
    volumes:
      - neo4j_data:/data

  api:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      neo4j:
        condition: service_started
    environment:
      NEO4J_URI: bolt://neo4j:7687

volumes:
  neo4j_data:
```

### 3.3 `.env.example`

Template delle variabili d'ambiente per Docker.

---

## Gruppo 4 — Entry point e CLI aggiornato

### 4.1 `src/main.py` — Nuovo sottocomando `serve`

```bash
uv run python -m src.main serve [--host 0.0.0.0] [--port 8000]
```

Lancia `uvicorn` programmaticamente.

---

## Struttura Directory Finale

```
src/
├── api/
│   ├── __init__.py
│   ├── app.py          ← FastAPI app + lifespan + exception handlers
│   ├── deps.py         ← Dependency injection (Neo4j driver)
│   ├── models.py       ← Request/Response Pydantic models
│   └── routes.py       ← Endpoint definitions
├── config.py
├── models.py
├── extractor.py
├── schema_builder.py
├── main.py
├── kg/
│   └── ...
└── routing/
    └── ...
```

## Ordine di Implementazione

1. **Gruppo 1** — Modelli + dipendenze (~15 min)
2. **Gruppo 2** — App + endpoint (~45 min)
3. **Gruppo 3** — Docker Compose (~20 min)
4. **Gruppo 4** — CLI `serve` + test (~15 min)

**Tempo totale stimato: ~1.5 ore**
