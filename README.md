# Teamprojekt KI-Copilot — Gruppe B: Geometriemodul

Extraktion geometrischer Zahnradparameter aus STEP-AP242-Dateien und Ausgabe als strukturiertes JSON.

## Projektstruktur

```
teamprojekt-ki-copilot/
│
├── src/                            ← Python-Quellcode (hier wird entwickelt)
│   ├── step_parser.py              Schritt 1: STEP-Datei laden, Flächen/Kanten
│   │                               klassifizieren, Bounding Box messen
│   ├── geometry_analyzer.py        Schritt 2: Zahnradparameter berechnen
│   │                               (z, m, d, d_f, β, Typ, Masse, Normen)
│   └── output_schema.py            Datenklasse GearParameters + JSON-Export
│
├── data/
│   └── examples/                   7 Test-STEP-Dateien (FreeCAD-Export,
│       └── *.step                  Stirn- und Schrägverzahnungen)
│
├── tests/
│   ├── test_geometry.py            44 Unit-Tests für Rechenfunktionen (pytest)
│   ├── accuracy_test.py            Integrationstest: Pipeline gegen Ground Truth
│   └── ground_truth.json           Sollwerte für alle 7 Test-STEP-Dateien
│
├── output/                         Generierte JSON-Ergebnisse (gitignored)
│
├── .vscode/
│   └── settings.json               VS Code Einstellungen (conda-Interpreter),
│                                   für alle Teammitglieder gleich
│
├── .gitlab-ci.yml                  CI/CD: Unit-Tests bei jedem Push,
│                                   Docker-Image bauen auf main
├── Dockerfile                      Container-Definition (conda + src/)
├── environment.yml                 conda-Umgebung (Python 3.11 + pythonocc)
├── README.md                       Diese Datei
└── SETUP_ANLEITUNG.md              Schritt-für-Schritt Setup für Teammitglieder
```

## Setup

```bash
conda env create -f environment.yml
conda activate gear-copilot
```

Vollständige Anleitung: [SETUP_ANLEITUNG.md](SETUP_ANLEITUNG.md)

## Verwendung

```bash
# Einzelne STEP-Datei analysieren
python src/step_parser.py --input data/examples/spur_m2_z20.step --output output/result.json

# Unit-Tests
python -m pytest tests/test_geometry.py -v

# Genauigkeitstest gegen Ground Truth
python tests/accuracy_test.py
```

## Algorithmus

Die Pipeline läuft in 5 Schritten:

1. **STEP laden** — pythonocc liest Geometrie und Topologie
2. **Bounding Box & Masse** — Außendurchmesser, Zahnbreite, Volumen
3. **Flächen analysieren** — Zylinder, Ebenen, Kegel, Tori klassifizieren
4. **Kanten analysieren** — Kantenzahl, Kantenlängen, Passfedernut-Erkennung
5. **Parameter ableiten** — Zahnzahl, Modul, Teilkreis, Fußkreis, Schrägungswinkel

### Zahnzahl- und Modul-Erkennung (v2)

Primärmethode: Modul-Enumeration über DIN-780-Normmoduln.
Für jeden Modul m: `z = d_a/m − 2`. Kandidaten mit ganzzahligem z werden
per Kanten-pro-Zahn-Nähe selektiert. Genauigkeit: **96 % (67/70 Parameter)**.

## Testergebnisse

| Datei | Korrekte Parameter |
|---|---|
| spur_m2_z20 | 10/10 |
| spur_m2_z30 | 10/10 |
| spur_m3_z15 | 10/10 |
| spur_m5_z10 | 10/10 |
| helical_m2_z25_b15 | 8/10 |
| helical_m2_z25_b20 | 10/10 |
| helical_m3_z20_b30 | 9/10 |
| **Gesamt** | **67/70 (96 %)** |

