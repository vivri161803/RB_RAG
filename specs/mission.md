# Mission — Rules Retrieval Pipeline

## Scopo del Progetto

**Rules Retrieval** è una pipeline CLI in Python che, data la descrizione testuale di un prodotto/asset (immobile, azienda o attività commerciale), individua automaticamente le regole di validazione ad esso applicabili e le esporta come schema Pydantic JSON.

Il sistema si basa su un **Knowledge Graph (KG) ontologico** caricato su Neo4j, costruito a partire dalle regole di dominio contenute in `rules/rules.json` (tassonomia Dometria Connect).

---

## Problema Risolto

La tassonomia Dometria Connect prevede ~3 macro-categorie (livello 1) e ~90 sotto-categorie (livello 2), ciascuna con un insieme specifico di campi obbligatori e opzionali. Determinare manualmente quale insieme di regole applicare a un nuovo prodotto è lento e error-prone.

**Rules Retrieval automatizza questo processo** tramite un routing LLM + vector search + reranking, senza richiedere intervento umano.

---

## Utenti Target

- **Sviluppatori backend** che devono validare inserimenti di asset nel CRM Dometria Connect.
- **Data engineer** che alimentano pipeline di bulk insert con dati semi-strutturati.
- **Integratori** che richiedono lo schema di validazione via CLI per generare form dinamici o contratti di input.

---

## Flusso di Alto Livello

```
rules/rules.json
      │
      ▼
[FASE 1] KG Builder ──────────────────────────────► Neo4j
      │  (NER, NED, embedding, Cypher load)
      │
[FASE 2] Two-Stage Router   ◄── descrizione prodotto (stdin / argomento CLI)
      │  1. LLM → livello 1 + riassunto
      │  2. Vector search cosine top-K=5 → livelli 2 candidati
      │  3. LLM Reranking → livello 2 finale
      │
[FASE 3] Rules Extractor
      │  Cypher query: livello 1 + livello 2 → lista attributi
      │
[FASE 4] Schema Builder
         Pydantic create_model → JSON schema validato
         OUTPUT: rules_schema.json
```

---

## Confini del Sistema (Scope)

**In scope:**
- Ingestion di `rules/rules.json` e costruzione KG su Neo4j
- Routing testuale → livello 1 + livello 2
- Estrazione regole via Cypher
- Generazione schema Pydantic runtime
- Interfaccia esclusivamente CLI


**Out of scope (v1):**
- API REST o interfaccia web
- Supporto multi-lingua (solo italiano)
- Fine-tuning dei modelli LLM
- Aggiornamento incrementale del KG (solo rebuild completo)