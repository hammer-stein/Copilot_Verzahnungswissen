"""
schema.py – Datenstrukturen und Lader für das Domänen-Metadatenschema.

Das Schema beschreibt, welche Felder aus Chunks extrahiert und beim Retrieval gefiltert werden.
Es wird aus einer externen YAML-Datei geladen (schemas/gears.yaml), sodass die Domäne
durch Austausch der YAML-Datei gewechselt werden kann, ohne Code zu ändern.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional

import yaml


# Bestimmt, wie das Feld im Stage-1-Filter ausgewertet wird.
# "exact" = String-Vergleich, "range" = Bereichsprüfung, "set" = Element in Menge
FilterType = Literal["exact", "range", "set"]


@dataclass(frozen=True)
class SchemaField:
    """Beschreibung eines einzelnen Metadatenfeldes. Wird im LLM-Prompt (Extraktion) und im Retriever-Filter genutzt."""
    name: str
    type: str
    filter_type: Optional[FilterType]   # None = Feld wird extrahiert, aber nicht gefiltert
    enum: Optional[list[str]] = None
    nullable: bool = False
    description: Optional[str] = None
    range_fields: Optional[list[str]] = None  # z.B. ["modul_min", "modul_max"]


@dataclass(frozen=True)
class MetadataSchema:
    """Vollständiges Domänenschema. filter_fields gibt nur die Felder zurück, die für Stage-1 relevant sind."""
    domain: str
    description: Optional[str]
    fields: list[SchemaField]
    extraction_prompt_hint: Optional[str] = None

    @property
    def filter_fields(self) -> list[SchemaField]:
        """Gibt nur Felder mit gesetztem filter_type zurück – diese fließen in den Qdrant-Stage-1-Filter ein."""
        return [f for f in self.fields if f.filter_type is not None]


def load_schema(path: Path) -> MetadataSchema:
    """
    Liest eine YAML-Schemadatei und wandelt sie in ein MetadataSchema-Objekt um.
    Fehlende optionale Felder werden durch Standardwerte ersetzt; nur name und type sind Pflicht.
    """
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))

    fields = []
    for f in raw.get("fields", []):
        fields.append(
            SchemaField(
                name=f["name"],
                type=f.get("type", "string"),
                filter_type=f.get("filter_type"),      # None wenn nicht angegeben
                enum=f.get("enum"),
                nullable=bool(f.get("nullable", False)),
                description=f.get("description"),
                range_fields=f.get("range_fields"),
            )
        )

    return MetadataSchema(
        domain=raw.get("domain", "unspecified"),
        description=raw.get("description"),
        fields=fields,
        extraction_prompt_hint=raw.get("extraction_prompt_hint"),
    )
