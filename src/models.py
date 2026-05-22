"""
src/models.py
-------------
Modelli Pydantic condivisi per tutto il progetto.
Definisce entità del KG, output strutturati LLM e aggregati.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════
# Entità del Knowledge Graph
# ═══════════════════════════════════════════════════════════════


class Level1Node(BaseModel):
    """Macro-categoria (es. Immobili, Aziende, Attività Commerciali)."""

    name: str = Field(..., description="Identificativo univoco della macro-categoria")
    description: str = Field(..., description="Descrizione testuale della macro-categoria")
    name_embedding: list[float] = Field(
        default_factory=list,
        description="Embedding del nome/id (popolato post-estrazione)",
    )


class Level2Node(BaseModel):
    """Sotto-categoria (es. Villa, Bar, Logistica e Trasporti)."""

    name: str = Field(..., description="Identificativo univoco della sotto-categoria")
    description: str = Field(..., description="Descrizione testuale della sotto-categoria")
    description_embedding: list[float] = Field(
        default_factory=list,
        description="Embedding della descrizione (popolato post-estrazione)",
    )


class AttributeNode(BaseModel):
    """Attributo (campo) di validazione associato a un livello."""

    name: str = Field(..., description="Nome del campo (es. 'Superficie coperta (mq)')")
    field_type: str = Field(
        default="str",
        description="Tipo del campo fra: (string, number, boolean)",
    )
    description: str = Field(
        default="",
        description="Descrizione del campo",
    )
    mandatory: bool = Field(
        ...,
        description="True se il campo è obbligatorio (MANDATORY), False se opzionale",
    )
    name_embedding: list[float] = Field(
        default_factory=list,
        description="Embedding del nome (popolato post-estrazione)",
    )


# ═══════════════════════════════════════════════════════════════
# Strutture per l'estrazione LLM delle triple
# ═══════════════════════════════════════════════════════════════


class Triple(BaseModel):
    """Singola tripla soggetto-oggetto."""

    source: str = Field(..., description="ID del nodo sorgente")
    target: str = Field(..., description="ID/nome del nodo destinazione")


class KGChunk(BaseModel):
    """Output strutturato di una singola chiamata LLM per una macro-categoria.

    Contiene le entità estratte e le relazioni tra di esse.
    """

    level1: Level1Node = Field(..., description="La macro-categoria estratta")
    level2_list: list[Level2Node] = Field(
        ..., description="Le sotto-categorie appartenenti a questa macro-categoria"
    )
    attributes: list[AttributeNode] = Field(
        ..., description="Tutti gli attributi (obbligatori e opzionali) di tutti i livelli"
    )
    triples_belongs_to: list[Triple] = Field(
        ...,
        description="Relazioni (level2_id, level1_id): ogni Level2 BELONGS_TO un Level1",
    )
    triples_requires_l1: list[Triple] = Field(
        ...,
        description="Relazioni (level1_id, attribute_name): attributi richiesti dalla macro-categoria",
    )
    triples_requires_l2: list[Triple] = Field(
        ...,
        description="Relazioni (level2_id, attribute_name): attributi richiesti dalla sotto-categoria",
    )


# ═══════════════════════════════════════════════════════════════
# Grafo aggregato (unione di tutti i KGChunk)
# ═══════════════════════════════════════════════════════════════


class KGraph(BaseModel):
    """Knowledge Graph completo, aggregato da più KGChunk."""

    level1_nodes: list[Level1Node] = Field(default_factory=list)
    level2_nodes: list[Level2Node] = Field(default_factory=list)
    attributes: list[AttributeNode] = Field(default_factory=list)
    triples_belongs_to: list[Triple] = Field(default_factory=list)
    triples_requires_l1: list[Triple] = Field(default_factory=list)
    triples_requires_l2: list[Triple] = Field(default_factory=list)

    def merge_chunk(self, chunk: KGChunk) -> None:
        """Aggrega un KGChunk nel grafo, deduplicando gli attributi per nome."""
        self.level1_nodes.append(chunk.level1)
        self.level2_nodes.extend(chunk.level2_list)

        # Deduplicazione attributi per nome
        existing_names = {a.name for a in self.attributes}
        for attr in chunk.attributes:
            if attr.name not in existing_names:
                self.attributes.append(attr)
                existing_names.add(attr.name)

        self.triples_belongs_to.extend(chunk.triples_belongs_to)
        self.triples_requires_l1.extend(chunk.triples_requires_l1)
        self.triples_requires_l2.extend(chunk.triples_requires_l2)


# ═══════════════════════════════════════════════════════════════
# Output strutturati per il routing LLM (Phase 2 — definiti ora)
# ═══════════════════════════════════════════════════════════════


class RouterOutput(BaseModel):
    """Output dello Step 1 (LLM routing): identifica il livello 1."""

    level1_id: str = Field(
        ...,
        description="ID della macro-categoria individuata (Immobili, Aziende, o Attività Commerciali)",
    )
    summary: str = Field(
        ...,
        description="Riassunto conciso (max 100 parole) delle caratteristiche rilevanti per individuare il livello 2",
    )


class RerankerOutput(BaseModel):
    """Output dello Step 3 (LLM reranking): sceglie il livello 2 finale."""

    level2_id: str = Field(
        ...,
        description="ID della sotto-categoria scelta come più adeguata",
    )
    reason: str = Field(
        ...,
        description="Motivazione della scelta",
    )
