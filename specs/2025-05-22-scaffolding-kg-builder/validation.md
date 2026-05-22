# Validation — Phase 0 (Scaffolding) + Phase 1 (KG Builder)

## Test Automatici

### V1 — Config funzionante
```bash
uv run python -c "from src.config import settings; print(settings.model_dump())"
```
**Expected**: stampa un dizionario con tutti i campi (`NEO4J_URI`, `API`, `LLM_MODEL`, ecc.) senza errori.

### V2 — Import di tutti i modelli
```bash
uv run python -c "from src.models import Level1Node, Level2Node, AttributeNode, KGChunk, KGraph, RouterOutput, RerankerOutput; print('OK')"
```
**Expected**: `OK` senza errori.

### V3 — Build KG end-to-end
```bash
uv run python -m src.main build-kg --input rules/rules.json
```
**Expected**: 
- 3 chiamate LLM (una per macro-categoria)
- Embedding generati per tutti i nodi
- Deduplicazione attributi applicata
- Caricamento su Neo4j completato senza errori
- Riepilogo stampato con conteggi

### V4 — Verifica Neo4j (Cypher nel browser o via driver)
```cypher
MATCH (n:Level1) RETURN count(n) AS l1_count;
-- Expected: 3

MATCH (n:Level2) RETURN count(n) AS l2_count;
-- Expected: ~90

MATCH (n:Attribute) RETURN count(n) AS attr_count;
-- Expected: >100

MATCH ()-[r:BELONGS_TO]->() RETURN count(r) AS belongs_count;
-- Expected: ~90 (uno per Level2)

MATCH ()-[r:REQUIRES]->() RETURN count(r) AS requires_count;
-- Expected: >200
```

### V5 — Idempotenza
Eseguire `build-kg` due volte e verificare che i conteggi non raddoppino (grazie a `MERGE`).

---

## Verifica Manuale

- [x] Aprire Neo4j Browser e verificare visivamente il grafo
- [x] Verificare che `(Villa)-[:BELONGS_TO]->(Immobili)` esista
- [x] Verificare che `(Immobili)-[:REQUIRES]->(Attribute {name: "Prezzo richiesto (€)", mandatory: true})` esista

```
MATCH (l1:Level1 {name: "Immobili"})-[:REQUIRES]->(a:Attribute {name: "Prezzo richiesto (€)"})
RETURN l1.name, a.name, a.mandatory
```

- [x] Verificare che `(Villa)-[:REQUIRES]->(Attribute {name: "Superficie coperta (mq)"})` esista

```
MATCH (l2:Level2 {name: "Villa"})-[:REQUIRES]->(a:Attribute)
WHERE a.name CONTAINS "Superficie coperta"
RETURN l2.name, a.name, a.mandatory;
```

- [x] Verificare che i `description_embedding` dei Level2 abbiano dimensione >0

```
MATCH (l2:Level2)
RETURN l2.name, size(l2.description_embedding) AS emb_size
ORDER BY emb_size ASC
LIMIT 5;
```

---

## Criterio di Merge

L'implementazione è pronta quando:
1. ✅ V1-V5 passano tutti
2. ✅ Il grafo è ispezionabile in Neo4j Browser
3. ✅ Le triple BELONGS_TO e REQUIRES rispettano lo schema ontologico
4. ✅ Gli embedding sono popolati e hanno dimensione corretta
