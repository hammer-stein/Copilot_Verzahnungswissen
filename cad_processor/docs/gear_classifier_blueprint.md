# Blueprint: Gear Classifier & Router

> Architektur-Konzept für einen universellen Verzahnungs-Klassifikator mit
> typ-spezifischem Routing. Grundlage für die nächste Implementierungs-Session.
> Stand: 2026-06-13. Verankert im aktuellen Codestand (`gear_metrology.py`,
> `geometry_analyzer.py`, `step_parser.py`).

---

## 1. Kontext & Ziel

Aktuell läuft die Typbestimmung an zwei Stellen:
- **Primär:** `gear_metrology.extract_metrology()` liefert die Roh-Signale
  (`is_internal`, `is_bevel`, `helix_angle_deg`, `num_teeth`, `face_width`, …).
- **Mapping:** `geometry_analyzer._apply_metrology()` leitet daraus den `gear_type`
  ab (simple if/elif-Kette: bevel → internal → helical(≥5°) → spur).
- **Fallback (Heuristik):** `geometry_analyzer.detect_gear_type()` (Flächen-/Tori-
  Heuristik) deckt zusätzlich `worm`, `worm_wheel`, `rack` ab — aber unzuverlässig
  und nicht mit der Metrologie verzahnt.

**Problem:** Es gibt keine *einheitliche* Entscheidungsschicht. Stirn/Schräg/Innen/
Kegel funktionieren über die Metrologie; **Zahnstange (rack)**, **Schnecke (worm)**
und **Schneckenrad (worm_wheel)** fallen durch das Raster, weil sie die Grund-
annahme der Metrologie verletzen (rotationssymmetrischer Zahnkranz mit z ≥ 4
Winkelperioden).

**Ziel:** Ein **`gear_classifier.py`**-Modul, das (a) den Verzahnungstyp robust und
mit Konfidenz bestimmt und (b) zur **typ-spezifischen Mess-Strategie** routet.
Es konsolidiert die heutige if/elif-Logik *und* die Heuristik in *eine* nachvoll-
ziehbare, getestete Schicht.

---

## 2. Architektur-Überblick

```
 STEP-Datei
     │
     ▼
 step_parser.load_step()         ──►  TopoDS_Shape  (gehärtet, multi-solid)
     │
     ▼
 gear_classifier.classify(shape) ──►  GearClass { type, confidence, signals, route }
     │   (Stufe 0–2, nutzt find_rotation_axis + Vor-Signale)
     ▼
 ROUTER  ── dispatch nach route ──►  ┌─ rotational → extract_metrology() (heute)
                                     ├─ bevel      → extract_metrology() + back-cone snap
                                     ├─ worm       → measure_worm()      (NEU)
                                     └─ rack       → measure_rack()      (NEU)
     │
     ▼
 geometry_analyzer.analyze_gear_geometry(..., classification=…)
     │   (übernimmt type + route-Ergebnis als Primärquelle)
     ▼
 output_schema → JSON  (+ neuer Block "classification")
```

**Designprinzip:** Der Klassifikator entscheidet *zuerst* den Typ aus billigen
Vor-Signalen, *dann* wählt der Router die passende (ggf. teure) Mess-Strategie.
So zahlt man die teure Vermessung nur für den passenden Typ.

---

## 3. Zweistufiges Klassifikationsmodell

### Stufe 0 — Symmetrie-Triage (rotational vs. translational)
Aus den Hauptträgheitsmomenten (`find_rotation_axis` liefert sie bereits intern):
- **Zwei Momente ~gleich** (Verhältnis der Differenz zur Spanne < ~5 %) →
  **rotationssymmetrisch** → Achse = das „andersartige" Trägheitsmoment.
  → weiter mit Stufe 1.
- **Alle drei Momente verschieden** (kein Symmetrie-Paar) →
  **translatorisch / prismatisch** → Kandidat **RACK** (Zahnstange) oder Nicht-Gear.
  → Router: `measure_rack()`.

> Praktischer Zusatztest Rack: Bounding-Box stark elongiert (eine Achse ≫ die
> anderen) **und** periodische Zahnstruktur entlang der Längsachse auf einer Fläche.

### Stufe 1 — Zahnkranz-Erkennung (nur rotational)
`extract_metrology()` Vorlauf: Achse, planare Querschnitte, **längster Lauf
konstanter Winkelperiodenzahl** (`_longest_band`).
- **Kein Band gefunden** (keine Winkelperiodizität, z < 4) → Rohteil/kein Gear
  **ODER** Schnecke mit 1–3 Gängen (→ Sonderpfad, siehe Stufe 2/Worm).
- **Band gefunden** → Signale stehen bereit: `z`, `is_internal` (Innen- vs.
  Außenprofil-Band), `is_bevel` (Kopfradius-Steigung), `helix_angle_deg`,
  `aspect_ratio = face_width / d_a`.

### Stufe 2 — Typ-Entscheidung (Prioritätsreihenfolge)
Reihenfolge ist wichtig (spezifische vor generischen Typen):

```
1. RACK        (aus Stufe 0)
2. WORM        z(Gänge) ≤ 6  ∧  Steigungswinkel hoch  ∧  aspect_ratio > 1.5
3. WORM_WHEEL  eingeschnürt (Kehlung)  ∧  hoher Tori-Anteil
4. BEVEL       is_bevel (Kopfkegel-Steigung > tan 8°)
5. INTERNAL    Innenprofil-Band schlägt Außenprofil-Band
6. HELICAL     helix_angle ≥ 5–8°
7. SPUR        sonst (helix ≈ 0, zylindrisch, außen)
```

---

## 4. Erkennungslogik pro Typ (konkrete Signale)

| Typ | Primärsignal | Schwellenwert / Regel | Quelle (existierend) |
|-----|-------------|-----------------------|----------------------|
| **spur** | Helixwinkel ≈ 0, zylindrisch | β < 5°, `is_bevel`=F, außen | `_helix_angle`, Band |
| **helical** | Helixwinkel der Flanken | β ≥ 5–8° (Kreuzkorrelation, ±½ Zahnteilung-Fenster gg. Aliasing) | `_helix_angle` |
| **internal** | Zähne auf Innenkontur | Innenprofil-Band stärker als Außen (glatte Felge außen) | `_longest_band(z_in)` vs `z_out` |
| **bevel** | Kopfradius variiert linear über z (Kegel) | `|slope(r_a, z)| > tan(8°)`; γ-Snap auf exakte koaxiale OCC-Kegelfläche | `_linfit_slope`, `_snap_cone_angle_to_occ` |
| **worm** | wenige „Zähne" = Gänge + steile Helix + langes L/D | z(Gänge) ≤ 6 ∧ β > ~15° ∧ `aspect_ratio` > 1.5 | Band-z, `_helix_angle`, bbox |
| **worm_wheel** | gekehlte (eingeschnürte) Zahnköpfe | r_a(z) hat Minimum in Bandmitte (Hourglass) ∧ hoher Tori-Anteil | tip-Radienprofil über Band, `tori` |
| **rack** | keine Rotationsachse, lineare Zahnperiodik | Stufe-0: kein Trägheits-Symmetriepaar; Zähne periodisch entlang Längsachse | `find_rotation_axis` (Momente), Linear-Schnitt |

**Schlüssel-Abgrenzungen (Verwechslungsgefahr):**
- **worm vs. helical:** beide haben Helix. Unterscheidung über **z**: Schnecke hat
  1–6 Gänge (sehr kleines z), Schrägrad hat normales z (≫ 6). Zusätzlich L/D.
  *Achtung:* Schnecke mit 1 Gang erzeugt **z = 1** → fällt unter den Band-Floor
  (z ≥ 4) → eigener Vorab-Pfad nötig (siehe §6 Worm-Sonderpfad).
- **bevel vs. spur mit Fase:** Fasen erzeugen kleine Kegelflächen. Abgrenzung:
  Kopfkegel-Steigung über das **gesamte** Band signifikant (nicht nur an den
  Stirnkanten) — bereits über die Bandsteigung abgedeckt.
- **internal vs. external:** Innenprofil (min-r je Winkel-Bin) vs. Außenprofil
  (max-r); das stärkere/stabilere Band gewinnt (bereits implementiert).

---

## 5. Router → typ-spezifische Mess-Strategie

| Route | Strategie | Status |
|-------|-----------|--------|
| spur / helical / internal | planare Querschnitte (heute) → z, d_a, d_f, m, d, b, β, Bohrung | ✅ vorhanden |
| bevel | planare Querschnitte + Kopfkegel-γ-Snap (heute), 95-Perzentil-d_a, Schräg-Zahnbreite | ✅ vorhanden |
| **worm** | **axiale Gewinde-Analyse:** Steigung (Lead) entlang der Achse, Gangzahl = Band-z, Axialmodul m_x = Lead/(π·Gänge), Flankenwinkel, Außen-Ø | 🔜 NEU `measure_worm()` |
| **rack** | **lineare Querschnitt-Analyse:** Zahnteilung p entlang der Längsachse → m = p/π, Eingriffswinkel aus Flanke, Zahnhöhe, Länge | 🔜 NEU `measure_rack()` |

Beide neuen Mess-Strategien spiegeln das bestehende Querschnitt-Prinzip, nur in
einer anderen Geometrie (axial statt radial bzw. linear statt angular).

---

## 6. Sonderpfade & Konfliktauflösung

### Worm-Sonderpfad (vor Stufe 1)
Eine eingängige Schnecke hat keine ≥4 Winkelperioden → die Band-Erkennung
schlägt fehl. Daher **vor** der Band-Suche prüfen:
- `aspect_ratio = bbox_länge / d_außen > 1.5` **und**
- dominante helikale Kanten mit großer Steigung (`extract_edge_helix_data`
  zeigt durchgehende, schraubenförmige Kanten über die ganze Länge).
→ direkt Route `worm`, Band-Suche überspringen.

### Konfliktauflösung (mehrere Signale aktiv)
- **bevel ∧ helix > 0** → „spiral bevel" (Spiralkegelrad) — vorerst als `bevel`
  mit `helix_angle` annotieren.
- **internal ∧ helix > 0** → `internal_helical`.
- Bei widersprüchlichen Signalen gewinnt die **Prioritätsreihenfolge** aus §3,
  und die **Konfidenz wird gesenkt** (siehe §7).

---

## 7. Konfidenz-Modell

Jede Klassifikation erhält eine Konfidenz aus **Signalstärke** und **Trennschärfe**:
- **Signalstärke:** Bandlänge / Gesamtschnitte, Amplituden-zu-Radius-Verhältnis,
  Stabilität von z über das Band (geringe Streuung).
- **Trennschärfe (Margin):** Abstand zum zweitwahrscheinlichsten Typ
  (z. B. β=7° nahe der 5°-Schwelle → helical mit niedriger Konfidenz).
- **Mapping auf die bestehenden Konfidenz-Tiers** (`output_schema.C`):
  DIRECT 0.92 (eindeutig), CALC 0.82, FALLBACK 0.65 (Heuristik), HEURISTIC 0.45.

`gear_type` wird wie heute als `ParameterValue{value, unit:"", confidence}` ausgegeben.

---

## 8. Datenstruktur (Output-Erweiterung)

Neuer Block `classification` im JSON (additiv, bricht nichts):

```json
"classification": {
  "type": "helical",
  "confidence": 0.88,
  "route": "rotational",
  "signals": {
    "has_rotation_axis": true,
    "num_angular_periods": 25,
    "is_internal": false,
    "is_bevel": false,
    "helix_angle_deg": 15.2,
    "aspect_ratio": 0.4,
    "cone_slope": 0.01
  },
  "runner_up": {"type": "spur", "confidence": 0.31},
  "notes": "β=15.2° > 5° → Schrägverzahnung; klare Trennung zu spur"
}
```

`gear_type` (Top-Level) bleibt erhalten; `classification` liefert die Begründung
und die Roh-Signale für die nachgelagerte RAG-Pipeline.

---

## 9. Integration in den bestehenden Code

| Datei | Änderung |
|-------|----------|
| **`src/gear_classifier.py`** (NEU) | `classify(shape) -> GearClass`; kapselt Stufe 0–2 + Router-Entscheidung; nutzt `find_rotation_axis`, die Vor-Signale aus `extract_metrology` (ggf. in einen leichten „pre-pass" auslagern). |
| `src/gear_metrology.py` | `measure_worm()`, `measure_rack()` ergänzen; `extract_metrology()` ggf. in Vor-Signal-Pass + Mess-Pass aufteilen, damit der Klassifikator die Vor-Signale ohne Vollmessung bekommt. |
| `src/geometry_analyzer.py` | `_apply_metrology()` if/elif-Kette **durch** `classification.type` ersetzen; `detect_gear_type()` als reine Fallback-Heuristik behalten. |
| `src/step_parser.py` | `classify()` zwischen Laden und Analyse aufrufen; `classification` an `analyze_gear_geometry` durchreichen. |
| `src/output_schema.py` | Feld `classification: Optional[dict]` + `"classification"`-Block in `to_dict()`. |

**Wiederverwendbare Bausteine (nicht neu bauen):**
`find_rotation_axis`, `_orthonormal_frame`, `_axial_extent`, `_section_points`,
`_radial_profile`, `_count_periods`, `_longest_band`, `_helix_angle`,
`_snap_cone_angle_to_occ`, `extract_edge_helix_data` (step_parser),
`assign_norm_reference`, `calculate_tooth_profile`.

---

## 10. Test- & Validierungsplan

| Typ | Ground-Truth-Bedarf | vorhanden? |
|-----|--------------------|------------|
| spur | 2664N311 (m=0.5, z=15) | ✅ |
| bevel | 2515N11 (DP16, z=24) | ✅ |
| helical | 1 reale STEP **mit Datenblatt** (β bekannt) | ❌ benötigt |
| internal | 1 reale STEP (Hohlrad) | ❌ benötigt |
| worm | 1 Schnecke (Gänge, Lead) | ❌ benötigt |
| rack | 1 Zahnstange (Modul, Länge) | ❌ benötigt |
| worm_wheel | 1 Schneckenrad | ❌ benötigt |

- Erweiterung von `tests/ground_truth.json` um die fehlenden Typen.
- `tests/accuracy_test.py` zusätzlich auf **Klassifikations-Treffer** prüfen
  (Soll-`gear_type` == Ist), getrennt von den numerischen Parametern.
- Unit-Tests für `classify()` mit **synthetischen Signal-Dicts** (ohne STEP-Datei):
  schnelle, deterministische Abdeckung der Entscheidungslogik & Schwellen.
- Regressionsschutz: die 70 bestehenden Unit-Tests + 18/19 Accuracy müssen grün
  bleiben (Klassifikator darf spur/bevel nicht verschlechtern).

---

## 11. Offene Punkte & Risiken

1. **Schwellenwerte empirisch:** β-Grenze (5–8°), aspect_ratio (1.5), Kegel-Steigung
   (tan 8°) sind an wenigen Teilen geeicht → mit mehr Ground Truth nachjustieren.
2. **Worm mit 1 Gang** unterläuft den Band-Floor (z ≥ 4) → der Vorab-Worm-Pfad (§6)
   ist Pflicht, sonst „kein Gear".
3. **Rack-Vermessung** ist ein eigenständiges lineares Verfahren — Aufwand nicht
   unterschätzen (eigene Achsen-/Periodik-Logik).
4. **Spiral-/Hypoid-Kegelräder** (bevel ∧ helix) sind vorerst nur grob abgedeckt.
5. **Validierungslücke:** Für 5 von 7 Typen fehlen reale Dateien mit Datenblatt;
   ohne sie bleibt die Generalisierung unbestätigt (Overfitting-Gefahr — vgl. die
   Kegelrad-Erfahrung: nie an *einer* Probe tunen).

---

## 12. Empfohlene Umsetzungsreihenfolge (nächste Session)

1. `gear_classifier.classify()` mit Stufe 0–2 **nur für die bereits gemessenen
   Typen** (spur/helical/internal/bevel) — ersetzt die if/elif-Kette, additiver
   `classification`-Block, **keine** Verhaltensänderung → Regressionssicher.
2. Unit-Tests für die Entscheidungslogik (synthetische Signal-Dicts).
3. **Worm-Sonderpfad** + `measure_worm()` (sobald Schnecken-Ground-Truth da ist).
4. **Rack** (Stufe-0-Zweig) + `measure_rack()` (sobald Zahnstangen-Ground-Truth da ist).
5. `worm_wheel` zuletzt (komplexeste Geometrie).
```
