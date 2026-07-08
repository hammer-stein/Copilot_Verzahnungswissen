"""
csv_gear_mapper.py – CSV/Excel → GearParameters (cad_metadata).

Liest eine Tabellen-Datei mit Verzahnungs-Parametern und mappt erkannte Spalten
auf die verschachtelte GearParameters-Struktur des cad_processor
(cad_processor/src/output_schema.py, Schema 2.0). Das Ergebnis ist formgleich
mit /cad/analyze und direkt als `cad_metadata` für /ask verwendbar – der
Inspector im Frontend rendert es ohne Anpassung.

Konvention: EINE CSV beschreibt EIN Bauteil. Es wird die erste Datenzeile
verwendet, die erkennbare Verzahnungs-Werte (Modul, Zähnezahl oder Typ) trägt.
Mehrzeilige Stücklisten gehören in die Wissensbasis (Upload in der
Dokumentbibliothek), nicht in den Bauteildaten-Kanal.

Bewusst OHNE Import aus cad_processor/: der Import von step_parser würde
pythonocc-core (Conda) voraussetzen; die Dict-Struktur wird hier nachgebaut.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from app.implementations.tabular_loader_pandas import read_dataframe

SCHEMA_VERSION = "2.0"

# Entspricht Tier DIRECT in cad_processor/src/output_schema.py (class C):
# der Wert wurde explizit angegeben, nicht aus Geometrie geschätzt.
DIRECT_CONFIDENCE = 0.92

_UMLAUTS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})

# Platzhalter, die als „nicht angegeben" gelten.
_EMPTY_VALUES = {"", "-", "–", "n/a", "na", "nan", "none", "null"}


def _norm_header(header: Any) -> str:
    """Normalisiert Spaltennamen für den Alias-Vergleich: 'Modul (mm)' → 'modul'."""
    s = str(header).strip().lower().translate(_UMLAUTS)
    s = re.sub(r"[\(\[\{].*?[\)\]\}]", "", s)  # Einheiten-Klammern entfernen
    return re.sub(r"[^a-z0-9]", "", s)


# Kanonischer GearParameters-Key → akzeptierte Spaltennamen (normalisiert, DE + EN
# inkl. DIN-Kurzzeichen). Erweiterbar ohne weitere Code-Änderung.
_COLUMN_ALIASES: dict[str, set[str]] = {
    "gear_type": {"verzahnungstyp", "zahnradtyp", "geartype", "bauart", "typ", "type"},
    "module_mm": {"modul", "modulmm", "module", "modulemm", "normalmodul", "m"},
    "num_teeth": {"zaehnezahl", "zahnzahl", "anzahlzaehne", "numteeth", "teeth", "z"},
    "pressure_angle_deg": {"eingriffswinkel", "eingriffswinkeldeg", "pressureangle", "pressureangledeg", "alpha"},
    "helix_angle_deg": {"schraegungswinkel", "schraegungswinkeldeg", "helixangle", "helixangledeg", "beta"},
    "profile_shift_x": {"profilverschiebung", "profilverschiebungsfaktor", "profileshift", "profileshiftx", "x"},
    "pitch_diameter_mm": {"teilkreis", "teilkreisdurchmesser", "pitchdiameter", "pitchdiametermm", "d"},
    "outer_diameter_mm": {"kopfkreis", "kopfkreisdurchmesser", "aussendurchmesser", "outerdiameter", "outerdiametermm", "da"},
    "root_diameter_mm": {"fusskreis", "fusskreisdurchmesser", "rootdiameter", "rootdiametermm", "df"},
    "face_width_mm": {"zahnbreite", "breite", "facewidth", "facewidthmm", "b"},
    "material": {"werkstoff", "material"},
    # Das Frontend zeigt material_context.tolerance_class als „Härte" und
    # quality_class_din als „Qualität" an – CSV-Spalten entsprechend zuordnen.
    "tolerance_class": {"haerte", "oberflaechenhaerte", "toleranzklasse", "toleranceclass", "hardness"},
    "quality_class_din": {"qualitaet", "verzahnungsqualitaet", "qualitaetsklasse", "qualityclassdin"},
    "part_name": {"bezeichnung", "benennung", "name", "partname"},
    "part_number": {"bauteilid", "teilenummer", "artikelnummer", "partnumber", "sachnummer", "id", "nr"},
}

# Spalten, deren Vorhandensein eine Zeile als Verzahnungs-Datensatz qualifiziert.
_GEAR_SIGNAL_KEYS = ("module_mm", "num_teeth", "gear_type")

# Deutsche/freie Typbezeichnungen → gear_type-Enum (GEAR_TYPE_LABELS im Frontend).
_GEAR_TYPE_VALUES = {
    "stirnrad": "spur", "geradverzahnt": "spur", "spur": "spur",
    "schraegverzahnung": "helical", "schraegverzahnt": "helical",
    "schraegstirnrad": "helical", "helical": "helical",
    "kegelrad": "bevel", "bevel": "bevel",
    "innenverzahnung": "internal", "hohlrad": "internal", "internal": "internal",
    "schnecke": "worm", "schneckenrad": "worm", "worm": "worm",
    "zahnstange": "rack", "rack": "rack",
}


def _is_empty(value: Any) -> bool:
    if value is None or pd.isna(value):
        return True
    return str(value).strip().lower() in _EMPTY_VALUES


def _parse_number(raw: Any) -> Optional[float]:
    """Zahl aus Zellwert: deutsches Komma, angehängte Einheiten ('3,0 mm', '20°') tolerieren."""
    if _is_empty(raw):
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw).strip().replace(",", ".")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


def _pv(value: Any, unit: str) -> dict:
    """Serialisiert einen Wert im ParameterValue-Format {value, unit, confidence}."""
    return {"value": value, "unit": unit, "confidence": DIRECT_CONFIDENCE}


def _map_columns(df: pd.DataFrame) -> dict[str, str]:
    """Ordnet DataFrame-Spalten den kanonischen GearParameters-Keys zu (erste passende gewinnt)."""
    col_map: dict[str, str] = {}
    for col in df.columns:
        key = _norm_header(col)
        for canonical, aliases in _COLUMN_ALIASES.items():
            if key in aliases and canonical not in col_map:
                col_map[canonical] = col
                break
    return col_map


def _pick_row(df: pd.DataFrame, col_map: dict[str, str]) -> tuple[int, pd.Series]:
    """Erste Datenzeile mit gefüllten Verzahnungs-Signal-Spalten; sonst erste Zeile."""
    signal_cols = [col_map[k] for k in _GEAR_SIGNAL_KEYS if k in col_map]
    for idx, row in df.iterrows():
        if any(not _is_empty(row[c]) for c in signal_cols):
            return int(idx), row
    return 0, df.iloc[0]


def map_tabular_to_gear_parameters(file_path: str | Path) -> dict:
    """
    Hauptfunktion: Tabellen-Datei → GearParameters-Dict (Schema 2.0).
    Wirft ValueError, wenn die Datei leer ist oder keine Verzahnungs-Spalten erkennbar sind.
    """
    path = Path(file_path)
    df = read_dataframe(path)
    if df.empty:
        raise ValueError(f"Tabellen-Datei enthält keine Datenzeilen: {path.name}")

    col_map = _map_columns(df)
    if not any(k in col_map for k in _GEAR_SIGNAL_KEYS):
        raise ValueError(
            "CSV enthält keine erkennbaren Verzahnungs-Spalten "
            "(erwartet z.B. Modul, Zähnezahl oder Verzahnungstyp)."
        )

    row_idx, row = _pick_row(df, col_map)

    def cell(key: str) -> Any:
        col = col_map.get(key)
        if col is None:
            return None
        value = row[col]
        return None if _is_empty(value) else value

    def num_pv(key: str, unit: str, *, as_int: bool = False) -> Optional[dict]:
        n = _parse_number(cell(key))
        if n is None:
            return None
        return _pv(int(round(n)) if as_int else n, unit)

    # gear_type: freie Bezeichnung → Enum; unbekannte Begriffe unverändert durchreichen.
    gear_type_pv = None
    raw_type = cell("gear_type")
    if raw_type is not None:
        norm_type = _norm_header(raw_type)
        gear_type_pv = _pv(_GEAR_TYPE_VALUES.get(norm_type, str(raw_type).strip()), "")

    quality = _parse_number(cell("quality_class_din"))

    warnings: list[str] = []
    if len(df) > 1:
        warnings.append(
            f"CSV enthält {len(df)} Datenzeilen – Zeile {row_idx + 2} wurde als Bauteil "
            "interpretiert. Mehrzeilige Stücklisten gehören in die Wissensbasis."
        )
    unmapped = [str(c) for c in df.columns if c not in col_map.values()]
    if unmapped:
        warnings.append(f"Nicht zugeordnete Spalten: {', '.join(unmapped)}")

    # Formgleich mit GearParameters.to_dict() (cad_processor/src/output_schema.py).
    return {
        "schema_version": SCHEMA_VERSION,
        "source_file": path.name,
        "filename": path.name,
        "gear_type": gear_type_pv,
        "overall_confidence": DIRECT_CONFIDENCE,

        "basic_geometry": {
            "outer_diameter_mm": num_pv("outer_diameter_mm", "mm"),
            "root_diameter_mm": num_pv("root_diameter_mm", "mm"),
            "pitch_diameter_mm": num_pv("pitch_diameter_mm", "mm"),
            "face_width_mm": num_pv("face_width_mm", "mm"),
        },

        "tooth_profile": {
            "num_teeth": num_pv("num_teeth", "", as_int=True),
            "module_mm": num_pv("module_mm", "mm"),
            "helix_angle_deg": num_pv("helix_angle_deg", "deg"),
            "pressure_angle_deg": num_pv("pressure_angle_deg", "deg"),
            "profile_shift_x": num_pv("profile_shift_x", ""),
        },

        "topology": {},

        "material_context": {
            "material": (str(cell("material")).strip() if cell("material") is not None else None),
            "tolerance_class": (str(cell("tolerance_class")).strip() if cell("tolerance_class") is not None else None),
            "quality_class_din": (int(quality) if quality is not None else None),
        },

        "metadata": {
            "part_name": (str(cell("part_name")).strip() if cell("part_name") is not None else None),
            "part_number": (str(cell("part_number")).strip() if cell("part_number") is not None else None),
            "created_by": "csv_gear_mapper",
        },

        "extraction_quality": {
            "warnings": warnings,
            "extraction_notes": {
                "source": "csv_gear_mapper",
                "row_index": row_idx,
                "mapped_columns": {k: str(v) for k, v in col_map.items()},
            },
        },

        "hints": {},
    }
