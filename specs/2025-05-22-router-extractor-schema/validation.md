# Validazione — Phase 2-4: Router → Extractor → Schema Builder

## V1 — Phase 2: Routing corretto

Test manuale con 5 descrizioni di prodotti diversi (almeno uno per macro-categoria).

### Descrizioni di test

| # | Descrizione | Level1 Atteso | Level2 Atteso |
|---|---|---|---|
| 1 | "Villa con piscina in Toscana, 500 mq, 10 camere, parco 2 ha" | Immobili | Villa |
| 2 | "Ristorante nel centro di Milano, 20 coperti, cucina italiana" | Attività Commerciali | Ristorante |
| 3 | "Azienda manifatturiera settore plastica, 50 dipendenti, fatturato 5M" | Aziende | Manifatturiera |
| 4 | "Hotel 4 stelle a Rimini, 80 camere, spa e ristorante" | Immobili | Hotel |
| 5 | "Bar tabaccheria in zona stazione, licenza completa" | Attività Commerciali | Bar |

### Comandi di verifica

```bash
uv run python -m src.main route --description "Villa con piscina in Toscana, 500 mq, 10 camere, parco 2 ha"
uv run python -m src.main route --description "Ristorante nel centro di Milano, 20 coperti, cucina italiana"
uv run python -m src.main route --description "Azienda manifatturiera settore plastica, 50 dipendenti, fatturato 5M"
uv run python -m src.main route --description "Hotel 4 stelle a Rimini, 80 camere, spa e ristorante"
uv run python -m src.main route --description "Bar tabaccheria in zona stazione, licenza completa"
```

**Criterio:** routing corretto in ≥4/5 casi.

---

## V2 — Phase 3: Estrazione attributi

```bash
# Attributi macro + specifici Villa
uv run python -m src.main extract --level1 Immobili --level2 Villa

# Attributi macro + specifici Ristorante
uv run python -m src.main extract --level1 "Attività Commerciali" --level2 Ristorante
```

### Verifiche

- [x] Output contiene sia attributi L1 (es. "Regione", "Prezzo richiesto (€)") che L2 specifici (es. "Piscina (Sì/No)" per Villa)
- [x] Nessun attributo duplicato
- [x] Attributi mandatory/optional correttamente marcati
- [x] Attributi ordinati: mandatory prima, optional dopo

---

## V3 — Phase 4: JSON Schema

```bash
# Pipeline completa → JSON schema
uv run python -m src.main run --description "Villa con piscina in Toscana, 500 mq" --output schema.json
```

### Verifiche

- [x] File `schema.json` generato
- [ ] Schema JSON valido (parsabile con `json.load`)

```bash
uv run python -c "
import json
with open('schema.json') as f:
    s = json.load(f)
print('✅ JSON valido')
print(f'Campi totali: {len(s[\"properties\"])}')
print(f'Required: {len(s.get(\"required\", []))}')
for name, prop in list(s['properties'].items())[:5]:
    print(f'  {name}: {prop.get(\"type\", prop.get(\"anyOf\", \"?\"))}')
"
```

- [x] Campi mandatory senza valore default in `required`
- [ ] Campi optional con tipo `Optional[T]` (nullable in JSON schema)

```bash
uv run python -c "
import json
with open('schema.json') as f:
    s = json.load(f)
required = set(s.get('required', []))
for name, prop in s['properties'].items():
    if name not in required:
        is_nullable = 'anyOf' in prop and any(t.get('type') == 'null' for t in prop['anyOf'])
        print(f'  {name}: nullable={is_nullable}  →  {prop}')
"

```
- [x] Tipi corretti: float per "mq"/"€", bool per "Sì/No", int per "n."/"numero"

### Test su 3 macro-categorie

```bash
uv run python -m src.main run --description "Villa in Toscana" --output schema_immobili.json
uv run python -m src.main run --description "Azienda logistica" --output schema_aziende.json
uv run python -m src.main run --description "Bar in centro" --output schema_commerciali.json
```

- [x] Tutti e 3 i file generati con schema valido

---

## Criterio di Merge

Tutti i check V1-V3 superati → merge su master.
