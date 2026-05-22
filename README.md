# Rules Retrieval Pipeline

Pipeline CLI in Python che, data la descrizione testuale di un prodotto/asset (immobile, azienda o attività commerciale), individua automaticamente le regole di validazione applicabili e le esporta come **JSON Schema**.

Il sistema si basa su un **Knowledge Graph ontologico** (Neo4j), costruito dalla tassonomia [Dometria Connect](rules/rules.json), e su un routing a 3 stadi (LLM → vector search → LLM reranking).

## Architettura

```
rules/rules.json
      │
      ▼
[FASE 1] KG Builder ──────────────────────────────► Neo4j
      │  Parsing deterministico + embedding OpenRouter
      │
[FASE 2] Three-Stage Router   ◄── descrizione prodotto
      │  1. LLM → Level1 + summary
      │  2. embed(summary) ⊗ description_embedding → top-K Level2
      │  3. LLM Reranking → Level2 finale
      │
[FASE 3] Rules Extractor
      │  Cypher query: Level1 + Level2 → lista attributi
      │
[FASE 4] Schema Builder
         Pydantic create_model → JSON Schema
         OUTPUT: schema.json
```

### Dettaglio Routing (Fase 2)

Il routing è una pipeline a 3 stadi progettata per combinare comprensione semantica (LLM) e retrieval veloce (vector search):

| Step | Input | Processo | Output |
|---|---|---|---|
| **1. LLM Router** | Descrizione utente | L'LLM identifica la macro-categoria e genera un riassunto arricchito | `level1` + `summary` |
| **2. Vector Search** | `summary` dello Step 1 | L'embedding del summary viene confrontato (cosine similarity) con i `description_embedding` dei Level2 nel KG | Top-K candidati Level2 |
| **3. LLM Reranker** | Descrizione + K candidati | L'LLM sceglie il Level2 più appropriato tra i candidati | `level2` + `reason` |

> **Perché il summary e non la descrizione originale?**
> L'LLM allo Step 1 arricchisce e normalizza la descrizione dell'utente (che può essere breve o ambigua) in un testo più strutturato e semanticamente denso, migliorando la qualità del matching vettoriale allo Step 2.


### Schema del Knowledge Graph

```
(:Level1)─[:REQUIRES]→(:Attribute)
    ▲
    │ [:BELONGS_TO]
    │
(:Level2)─[:REQUIRES]→(:Attribute)
```

| Nodo | Quantità | Proprietà |
|---|---|---|
| `Level1` | 3 | `name`, `description`, `name_embedding` |
| `Level2` | 92 | `name`, `description`, `description_embedding` |
| `Attribute` | 379 | `name`, `field_type`, `description`, `mandatory`, `name_embedding` |

---

## Setup

### Prerequisiti

- **Python 3.13+**
- **[uv](https://docs.astral.sh/uv/)** — gestore pacchetti
- **Neo4j** (locale o Docker)
- **API key OpenRouter**

### 1. Clona e installa

```bash
git clone <repo-url>
cd BulkInsert_RulesExtraction
uv sync
```

### 2. Configura `.env`

```env
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<la-tua-password>

# OpenRouter
API=sk-or-v1-<la-tua-chiave>
LLM_MODEL=openai/gpt-oss-20b
EMBEDDING_MODEL=openai/text-embedding-3-small

# Pipeline
TOP_K=5
```

### 3. Avvia Neo4j

Con Docker:

```bash
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/<la-tua-password> \
  neo4j:latest
```

Oppure [Neo4j Desktop](https://neo4j.com/download/).

### 4. Costruisci il Knowledge Graph

```bash
uv run python -m src.main build-kg
```

Con arricchimento LLM delle descrizioni degli attributi (opzionale):

```bash
uv run python -m src.main build-kg --enrich
```

---

## Comandi CLI

### `build-kg` — Costruisce il Knowledge Graph

Parsing deterministico di `rules/rules.json` → embedding → caricamento su Neo4j.

```bash
uv run python -m src.main build-kg [--input rules/rules.json] [--enrich]
```

| Flag | Descrizione |
|---|---|
| `--input` | Percorso al file rules.json (default: `rules/rules.json`) |
| `--enrich` | Genera descrizioni attributi via LLM (opzionale) |

---

### `route` — Identifica Level1 e Level2

Data una descrizione testuale, esegue il routing a 3 stadi per identificare macro-categoria e sotto-categoria.

```bash
uv run python -m src.main route --description "Villa con piscina in Toscana, 500 mq, 10 camere"
```

Output:

```
╔══════════════════════════════════════════╗
║           ROUTING COMPLETATO             ║
╠══════════════════════════════════════════╣
║  Level1:  Immobili                       ║
║  Level2:  Villa                          ║
╠══════════════════════════════════════════╣
║  Reason:  La descrizione corrisponde...  ║
╚══════════════════════════════════════════╝
```

---

### `extract` — Estrae gli attributi applicabili

Dato Level1 e Level2, query Cypher per gli attributi (mandatory + optional), deduplicati.

```bash
uv run python -m src.main extract --level1 Immobili --level2 Villa
```

Output: tabella con nome, tipo, obbligatorietà e descrizione di ogni attributo.

---

### `run` — Pipeline completa (descrizione → JSON Schema)

Esegue in sequenza: **routing → estrazione → generazione schema** e salva il JSON Schema su file.

```bash
uv run python -m src.main run --description "Villa con piscina in Toscana" --output schema.json
```

| Flag | Descrizione |
|---|---|
| `--description` | Descrizione testuale del prodotto/asset |
| `--output` | Percorso file di output (default: `schema.json`) |

---

## Deploy con Docker

Tutti i file per il deploy sono nella cartella [`docker/`](docker/):

```
docker/
├── Dockerfile            # Immagine Python 3.13 + uv + app
└── docker-compose.yml    # Stack: Neo4j + API
```

### Prerequisiti

- **Docker** e **Docker Compose** installati
- File `.env` configurato nella root del progetto (usa `.env.example` come base)

### Quick Start

```bash
# 1. Configura le variabili d'ambiente
cp .env.example .env
# Modifica .env con la tua API key OpenRouter e password Neo4j

# 2. Avvia lo stack (Neo4j + API)
docker compose -f docker/docker-compose.yml up -d

# 3. Verifica che tutto sia attivo
docker compose -f docker/docker-compose.yml ps
curl http://localhost:8000/health

# 4. Costruisci il Knowledge Graph (prima esecuzione)
curl -X POST http://localhost:8000/build-kg \
  -H "Content-Type: application/json" \
  -d '{"enrich": true}'

# 5. Usa la pipeline
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"description": "Villa con piscina in Toscana, 500 mq"}'
```

### Gestione

```bash
# Visualizza i log
docker compose -f docker/docker-compose.yml logs -f api

# Stop
docker compose -f docker/docker-compose.yml down

# Stop + rimuovi i volumi Neo4j (reset completo)
docker compose -f docker/docker-compose.yml down -v

# Rebuild dopo modifiche al codice
docker compose -f docker/docker-compose.yml up -d --build
```

### Porte esposte

| Servizio | Porta | URL |
|---|---|---|
| API (FastAPI) | `8000` | `http://localhost:8000` |
| API Docs (Swagger) | `8000` | `http://localhost:8000/docs` |
| Neo4j Browser | `7474` | `http://localhost:7474` |
| Neo4j Bolt | `7687` | `bolt://localhost:7687` |

---

## Struttura del Progetto

```
BulkInsert_RulesExtraction/
├── .env                          # Configurazione (Neo4j, OpenRouter)
├── .env.example                  # Template variabili d'ambiente
├── pyproject.toml                # Dipendenze Python (uv)
├── docker/
│   ├── Dockerfile                # Container app (Python 3.13 + uv)
│   └── docker-compose.yml        # Stack completo (Neo4j + API)
├── rules/
│   └── rules.json                # Tassonomia Dometria Connect
├── specs/
│   ├── mission.md                # Obiettivi del progetto
│   ├── tech-stack.md             # Stack tecnologico
│   └── roadmap.md                # Roadmap di implementazione
└── src/
    ├── config.py                 # Caricamento .env e client factory
    ├── models.py                 # Pydantic models condivisi
    ├── extractor.py              # FASE 3: Cypher → attributi
    ├── schema_builder.py         # FASE 4: create_model → JSON Schema
    ├── main.py                   # CLI entrypoint (5 sottocomandi)
    ├── api/
    │   ├── app.py                # FastAPI app + lifespan + error handlers
    │   ├── deps.py               # Dependency injection (Neo4j driver)
    │   ├── models.py             # Request/Response Pydantic models
    │   └── routes.py             # Endpoint REST
    ├── kg/
    │   ├── builder.py            # FASE 1: parsing deterministico
    │   ├── embedder.py           # Embedding via OpenRouter
    │   └── neo4j_loader.py       # Caricamento su Neo4j
    └── routing/
        ├── __init__.py           # Pipeline routing orchestrata
        ├── llm_router.py         # FASE 2 Step 1: LLM → Level1
        ├── vector_search.py      # FASE 2 Step 2: cosine top-K
        └── reranker.py           # FASE 2 Step 3: LLM reranking
```

---

## API REST

Il servizio è disponibile anche come API REST (FastAPI). Avvio:

```bash
uv run python -m src.main serve [--host 0.0.0.0] [--port 8000]
```

Documentazione interattiva (Swagger): `http://localhost:8000/docs`

### Endpoint

| Metodo | Path | Descrizione |
|---|---|---|
| `GET` | `/health` | Health check (stato Neo4j) |
| `POST` | `/route` | Routing: descrizione → Level1 + Level2 |
| `POST` | `/extract` | Estrazione: Level1 + Level2 → attributi |
| `POST` | `/run` | Pipeline completa: descrizione → JSON Schema |
| `POST` | `/build-kg` | Trigger rebuild del Knowledge Graph |

### Esempi con `curl`

```bash
# Health check
curl http://localhost:8000/health

# Routing
curl -X POST http://localhost:8000/route \
  -H "Content-Type: application/json" \
  -d '{"description": "Villa con piscina in Toscana, 500 mq"}'

# Estrazione attributi
curl -X POST http://localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d '{"level1": "Immobili", "level2": "Villa"}'

# Pipeline completa → JSON Schema
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"description": "Hotel 4 stelle a Rimini, 80 camere"}' | python3 -m json.tool

# Rebuild KG
curl -X POST http://localhost:8000/build-kg \
  -H "Content-Type: application/json" \
  -d '{"enrich": false}'
```



---

## Esempio End-to-End

### Via CLI

```bash
# 1. Costruisci il KG (una sola volta)
uv run python -m src.main build-kg --enrich

# 2. Genera lo schema per un prodotto
uv run python -m src.main run \
  --description "Hotel 4 stelle a Rimini, 80 camere, spa e ristorante" \
  --output schema_hotel.json

# 3. Ispeziona il risultato
cat schema_hotel.json | python3 -m json.tool
```

### Via API

```bash
# 1. Avvia il server
uv run python -m src.main serve

# 2. Costruisci il KG
curl -X POST http://localhost:8000/build-kg -H "Content-Type: application/json" -d '{}'

# 3. Genera lo schema
curl -s -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"description": "Hotel 4 stelle a Rimini"}' | python3 -m json.tool
```