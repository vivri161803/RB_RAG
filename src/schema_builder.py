"""
src/schema_builder.py
---------------------
Phase 4 — Schema Builder.

Genera un modello Pydantic runtime dalla lista di attributi estratti
e lo serializza come JSON Schema.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from pydantic import Field, create_model

from src.models import AttributeNode

logger = logging.getLogger(__name__)

# Mappa field_type (stringa dal KG) → tipo Python
TYPE_MAP: dict[str, type] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
}


def build_schema(attributes: list[AttributeNode]) -> type:
    """Costruisce un modello Pydantic dinamico dalla lista di attributi.

    - `mandatory=True` → campo obbligatorio (Field(...))
    - `mandatory=False` → `Optional[T] = None`

    Args:
        attributes: Lista di AttributeNode dal Rules Extractor.

    Returns:
        Classe Pydantic dinamica (`type[BaseModel]`).
    """
    fields: dict = {}

    for attr in attributes:
        python_type = TYPE_MAP.get(attr.field_type, str)
        # Sanitizza il nome del campo per Python (spazi → underscore, rimuovi caratteri speciali)
        field_name = _sanitize_field_name(attr.name)

        if attr.mandatory:
            fields[field_name] = (
                python_type,
                Field(..., description=attr.description, title=attr.name),
            )
        else:
            fields[field_name] = (
                Optional[python_type],
                Field(None, description=attr.description, title=attr.name),
            )

    model = create_model("ProductSchema", **fields)

    logger.info(
        "Schema generato: %d campi (%d required, %d optional)",
        len(fields),
        sum(1 for a in attributes if a.mandatory),
        sum(1 for a in attributes if not a.mandatory),
    )

    return model


def _sanitize_field_name(name: str) -> str:
    """Converte un nome di attributo in un nome Python valido.

    Es: "Prezzo richiesto (€)" → "prezzo_richiesto_eur"
    """
    import re

    # Sostituzioni specifiche
    result = name.lower()
    result = result.replace("(€)", "eur")
    result = result.replace("€", "eur")
    result = result.replace("(mq)", "mq")
    result = result.replace("(ha)", "ha")
    result = result.replace("(km)", "km")
    result = result.replace("(ml)", "ml")
    result = result.replace("(m)", "m")
    result = result.replace("(mc)", "mc")
    result = result.replace("(n.)", "n")
    result = result.replace("sì/no", "flag")
    result = result.replace("/", "_")
    result = result.replace("'", "")
    result = result.replace("'", "")

    # Rimuovi tutto ciò che non è alfanumerico o underscore
    result = re.sub(r"[^a-z0-9_]", "_", result)
    # Collassa underscore multipli
    result = re.sub(r"_+", "_", result)
    # Rimuovi underscore iniziali/finali
    result = result.strip("_")

    return result


def export_json_schema(model: type) -> dict:
    """Serializza il modello Pydantic come JSON Schema.

    Args:
        model: Classe Pydantic creata da `build_schema()`.

    Returns:
        Dizionario JSON Schema.
    """
    return model.model_json_schema()


def save_json_schema(schema: dict, output_path: str | Path) -> None:
    """Salva il JSON Schema su file.

    Args:
        schema: Dizionario JSON Schema.
        output_path: Percorso del file di output.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)

    logger.info("JSON Schema salvato: %s", path)
