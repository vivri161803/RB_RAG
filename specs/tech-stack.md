# Tech Stack

## Linguaggio & Runtime

| Componente | Scelta | Note |
|---|---|---|
| Linguaggio | **Python 3.13** | versione già presente nel repo (`.python-version`) |
| Gestore dipendenze | **uv** | già inizializzato (`pyproject.toml`, `uv.lock`) |
| Env variables | **python-dotenv** | legge `.env` con `NEO4J_*` e `API` |

---

## Modelli LLM & Embedding

| Componente | Provider | Configurazione |
|---|---|---|
| LLM (routing + reranking) | **OpenRouter** | chiave `API` in `.env`; `LLM_MODEL` |
| Embedding | **OpenRouter** | stesso provider, `EMBEDDING_MODEL` |
| Provider ordering | **throughput** | `provider.order` ordinato per massimo throughput nelle chiamate OpenRouter |
| Client HTTP LLM | **openai** (compatibile OpenRouter) | base URL `https://openrouter.ai/api/v1` |

### Configurazione `.env` attesa

```env
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=...

# OpenRouter
API=sk-or-v1-...
LLM_MODEL=google/gemini-2.5-flash                  # modello per routing/reranking
EMBEDDING_MODEL=openai/text-embedding-3-small       # modello per embedding

# Pipeline
TOP_K=5                                             # candidati per vector search
```

---

## Validazione & Modellazione Dati

| Libreria | Uso |
|---|---|
| **Pydantic v2** | modelli strutturati per output LLM (routing, reranking), e `create_model` runtime per schema finale |
| **instructor** | patch del client OpenAI/OpenRouter per output Pydantic strutturato da LLM |

---

## Knowledge Graph

| Componente | Scelta | Note |
|---|---|---|
| Database grafo | **Neo4j** (locale) | connessione via bolt, credenziali in `.env` |
| Driver Python | **neo4j** (driver ufficiale) | sessioni sincrone |
| Query language | **Cypher** | per load, retrieval e traversal del grafo |

### Schema Ontologico Neo4j

**Nodi:**

| Label | Proprietà |
|---|---|
| `Level1` | `id`, `description`, `name_embedding: float[]` |
| `Level2` | `id`, `description`, `description_embedding: float[]` |
| `Attribute` | `name`, `field_type`, `description`, `name_embedding: float[]`, `mandatory: bool` |

**Relazioni:**

| Relazione | Da → A | Vincolo |
|---|---|---|
| `BELONGS_TO` | `Level2` → `Level1` | esclusività (ogni L2 appartiene a un solo L1) |
| `REQUIRES` | `Level1` → `Attribute` | campi macro-categoria |
| `REQUIRES` | `Level2` → `Attribute` | campi specifici sotto-categoria |

---

## NER / NED

| Tecnica | Libreria |
|---|---|
| **NER** | LLM-based (extraction prompt strutturato con Pydantic) |
| **NED** (Entity Disambiguation) | cosine similarity tra embedding del nome entità estratta e embedding dei nodi nel KG (`numpy` per il calcolo) |

---

## Librerie Python — Dipendenze

```toml
[project.dependencies]
pyyaml = ">=6.0"
pydantic = ">=2.0"
instructor = ">=1.0"
openai = ">=1.0"          # client compatibile OpenRouter
neo4j = ">=5.0"           # driver Neo4j
numpy = ">=1.26"          # cosine similarity
python-dotenv = ">=1.0"
```

---

## Struttura Directory Target

```
BulkInsert_RulesExtraction/
├── .env
├── pyproject.toml
├── rules/
│   ├── rules.yaml
│   ├── rules.json          ← input principale
│   └── process_rules.py
├── specs/
│   ├── mission.md
│   ├── tech-stack.md
│   └── roadmap.md
└── src/
    ├── __init__.py
    ├── config.py           ← carica .env, costanti
    ├── models.py           ← Pydantic models condivisi
    ├── kg/
    │   ├── __init__.py
    │   ├── builder.py      ← FASE 1: parsing JSON → grafo
    │   ├── neo4j_loader.py ← FASE 1: caricamento su Neo4j
    │   └── ned.py          ← NED cosine similarity
    ├── routing/
    │   ├── __init__.py
    │   ├── llm_router.py   ← FASE 2 step 1: LLM → Level1
    │   ├── vector_search.py← FASE 2 step 2: top-K cosine
    │   └── reranker.py     ← FASE 2 step 3: LLM reranking
    ├── extractor.py        ← FASE 3: Cypher query
    ├── schema_builder.py   ← FASE 4: Pydantic create_model
    └── main.py             ← CLI entrypoint
```
