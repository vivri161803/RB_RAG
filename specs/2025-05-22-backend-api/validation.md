# Validazione — Phase 5: Backend API (FastAPI)

## V1 — App startup e health check

### Test

```bash
# Avvio locale
uv run python -m src.main serve

# Health check
curl http://localhost:8000/health
```

### Verifiche

- [ ] Server si avvia senza errori su porta 8000
- [ ] `GET /health` risponde `200` con `{"status": "healthy", "neo4j": "connected"}`
- [ ] `GET /health` risponde `503` se Neo4j è spento
- [ ] OpenAPI docs disponibili su `http://localhost:8000/docs`

---

## V2 — Endpoint `/route`

### Test

```bash
curl -X POST http://localhost:8000/route \
  -H "Content-Type: application/json" \
  -d '{"description": "Villa con piscina in Toscana, 500 mq, 10 camere"}'
```

### Verifiche

- [ ] Risposta `200` con `level1`, `level2`, `reason`
- [ ] `level1` = "Immobili", `level2` = "Villa"
- [ ] Request senza `description` → `422` con errore Pydantic
- [ ] `description` vuota → risposta comunque (non crash)

---

## V3 — Endpoint `/extract`

### Test

```bash
curl -X POST http://localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d '{"level1": "Immobili", "level2": "Villa"}'
```

### Verifiche

- [ ] Risposta `200` con lista `attributes` e `count`
- [ ] `count` = 22 (come da CLI)
- [ ] Ogni attributo ha `name`, `field_type`, `description`, `mandatory`
- [ ] Nessun campo `name_embedding` nella risposta (dati interni esclusi)

---

## V4 — Endpoint `/run`

### Test

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"description": "Hotel 4 stelle a Rimini, 80 camere"}'
```

### Verifiche

- [ ] Risposta `200` con `level1`, `level2`, `schema`
- [ ] `schema` è un JSON Schema valido (contiene `properties`, `required`)
- [ ] I tipi nello schema corrispondono ai `field_type` degli attributi

---

## V5 — Endpoint `/build-kg`

### Test

```bash
curl -X POST http://localhost:8000/build-kg \
  -H "Content-Type: application/json" \
  -d '{"enrich": false}'
```

### Verifiche

- [ ] Risposta `200` con `status: "completed"` e `counts`
- [ ] `counts.level1_nodes` = 3, `counts.level2_nodes` = 92, `counts.attribute_nodes` = 379
- [ ] Eseguire `/route` dopo il rebuild → funziona correttamente

---

## V6 — Error handling

### Test

```bash
# Neo4j spento → POST /route
curl -X POST http://localhost:8000/route \
  -H "Content-Type: application/json" \
  -d '{"description": "test"}'
```

### Verifiche

- [ ] Neo4j spento: tutte le route rispondono `503` con messaggio chiaro
- [ ] Input malformato (non JSON): risponde `422`
- [ ] Errore OpenRouter: risponde `502`

---

## V7 — Docker Compose

### Test

```bash
docker compose up -d
curl http://localhost:8000/health

# Build KG dentro il container
curl -X POST http://localhost:8000/build-kg -H "Content-Type: application/json" -d '{}'

# Pipeline completa
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"description": "Ristorante nel centro di Milano"}'
```

### Verifiche

- [ ] `docker compose up -d` avvia sia Neo4j che l'API senza errori
- [ ] L'API comunica con Neo4j via rete Docker interna (`bolt://neo4j:7687`)
- [ ] `/build-kg` popola il grafo nel Neo4j containerizzato
- [ ] `/run` restituisce JSON Schema valido

---

## V8 — Coerenza CLI vs API

Verificare che i risultati dell'API siano identici a quelli della CLI:

```bash
# CLI
uv run python -m src.main extract --level1 Immobili --level2 Villa

# API
curl -s http://localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d '{"level1": "Immobili", "level2": "Villa"}' | python -m json.tool
```

### Verifiche

- [ ] Stesso numero di attributi
- [ ] Stessi nomi, tipi e flag mandatory
- [ ] Stessi attributi L1 e L2 presenti

---

## Criterio di Merge

Tutti i check V1-V8 superati → merge su master.
