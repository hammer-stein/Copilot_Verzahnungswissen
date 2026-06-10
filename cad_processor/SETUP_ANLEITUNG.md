# Setup-Anleitung — Teamprojekt KI Copilot
**Gruppe B: Geometrie-Modul**  

Diese Anleitung führt euch Schritt für Schritt durch das komplette Setup.  
Am Ende habt ihr alle dieselbe Entwicklungsumgebung und könnt gemeinsam am Projekt arbeiten.

---

## Übersicht: Was wir installieren

| Tool | Zweck |
|---|---|
| **Miniconda** | Python-Umgebungen verwalten |
| **VS Code** | Code-Editor |
| **Git** | Versionsverwaltung (meist schon vorhanden) |
| **pythonocc-core** | STEP-Dateien lesen (über conda) |

---

## Teil 1 — Miniconda installieren

Miniconda verwaltet unsere Python-Umgebung. Wir nutzen es statt pip, weil pythonocc native C++-Abhängigkeiten hat die pip nicht zuverlässig installieren kann.

### Mac (Intel)
1. Runterladen: https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.pkg
2. `.pkg`-Datei doppelklicken → Installer durchklicken
3. Terminal öffnen, testen:
```bash
conda --version
```
→ Erwartete Ausgabe: `conda 25.x.x`

Falls `command not found` erscheint:
```bash
~/miniconda3/bin/conda init zsh
```
Terminal schließen, neu öffnen, nochmal testen.

### Mac (Apple Silicon — M1/M2/M3)
1. Runterladen: https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.pkg
2. `.pkg`-Datei doppelklicken → Installer durchklicken
3. Terminal testen: `conda --version`
---

## Teil 2 — VS Code installieren

1. Runterladen: https://code.visualstudio.com
2. Installer ausführen → Standard-Einstellungen übernehmen
3. VS Code öffnen

### Erweiterungen installieren

In VS Code links auf das **Extensions-Icon** klicken (oder `Cmd+Shift+X` / `Strg+Shift+X`), folgende Erweiterungen suchen und installieren:

- **Python** (von Microsoft) — Python-Unterstützung
- **GitLens** (optional, aber empfohlen) — bessere Git-Übersicht

---

## Teil 3 — Git überprüfen

Git ist für die Zusammenarbeit über GitHub nötig. Auf Mac meist schon installiert.

```bash
git --version
```

Falls nicht installiert:
- **Mac:** `xcode-select --install` im Terminal eingeben

### Git mit euren Daten konfigurieren (einmalig, jeder für sich)

```bash
git config --global user.name "Vorname Nachname"
git config --global user.email "deine.email@student.kit.edu"
```

Überprüfen:
```bash
git config --global --list
```
→ Ihr solltet `user.name` und `user.email` sehen.

---

## Teil 4 — GitHub Repo klonen (in VS Code)

"Klonen" = das gemeinsame Projekt von GitHub auf euren Rechner runterladen.

1. VS Code öffnen
2. `Cmd+Shift+P` (Mac) oder `Strg+Shift+P` (Windows) drücken
3. `Git: Clone` eintippen → Enter
4. Diese URL einfügen:
```
https://github.com/hammer-stein/Copilot_Verzahnungswissen.git
```
5. Ordner wählen wo das Projekt gespeichert werden soll (z.B. `Dokumente`)
6. VS Code fragt "Would you like to open the cloned repository?" → **Open** klicken

Das Projekt ist jetzt lokal auf eurem Rechner. Der CAD-Prozessor-Code liegt im Unterordner `cad_processor/`.

---

## Teil 5 — conda-Umgebung erstellen

Jetzt installieren wir pythonocc und alle anderen Abhängigkeiten. Die `environment.yml` im Repo enthält alles was gebraucht wird.

### Terminal in VS Code öffnen

**Terminal → New Terminal** (oben in der Menüleiste)

Ein schwarzes Terminal-Panel öffnet sich unten. Ihr seid bereits automatisch im richtigen Projektordner.

### Umgebung erstellen

Im VS Code Terminal, ausgehend vom **Root-Ordner des Repos**:

```bash
conda env create -f cad_processor/environment.yml
```

> ⏳ Das dauert **3–5 Minuten** — pythonocc ist groß. Einfach warten bis die Eingabezeile wieder erscheint.

Wenn fertig, erscheint:
```
done
# To activate this environment, use:
# conda activate gear-copilot
```

### Umgebung aktivieren

```bash
conda activate gear-copilot
```

Ihr seht jetzt `(gear-copilot)` links im Terminal statt `(base)`.

### Installation testen

```bash
python -c "from OCC.Core.STEPControl import STEPControl_Reader; print('pythonocc OK')"
```

→ Erwartete Ausgabe: `pythonocc OK`

---

## Teil 6 — VS Code Python-Interpreter einstellen

VS Code muss wissen, dass es Python aus der `gear-copilot` Umgebung nutzen soll.

1. `Cmd+Shift+P` (Mac) oder `Strg+Shift+P` (Windows)
2. `Python: Select Interpreter` eintippen → Enter
3. In der Liste die Option mit `gear-copilot` wählen:
```
Python 3.11.x ('gear-copilot': conda)
```

Ab jetzt erkennt VS Code alle pythonocc-Imports korrekt (keine roten Unterstreichungen).

---

## Teil 7 — Täglicher Workflow mit Git

### Morgens: Neuesten Stand holen (pullen)

Bevor ihr anfangt zu coden, immer erst den aktuellen Stand vom Team holen:

```bash
git pull
```

Oder in VS Code: Unten in der Statusleiste auf das **↓↑ Sync-Symbol** klicken.

> ⚠️ Immer zuerst pullen bevor ihr anfangt — sonst gibt es Konflikte!

### Während dem Coden

Einfach normal in `src/` programmieren. conda-Umgebung nicht vergessen zu aktivieren:

```bash
conda activate gear-copilot
```

Skript testen:
```bash
python src/step_parser.py --input data/examples/zahnrad.stp
```

### Abends: Änderungen hochladen (pushen)

Wenn ihr fertig seid, eure Änderungen sichern und ins Team hochladen:

**Option A — In VS Code**

1. Links auf das **Source Control Icon** klicken (3 verbundene Punkte)
2. Ihr seht alle geänderten Dateien
3. In das **Message**-Feld oben eine kurze Beschreibung schreiben, z.B.:
   - `Zahnzahl-Algorithmus verbessert`
   - `Bugfix: Bounding Box bei schiefen Bauteilen`
   - `geometry_analyzer: Kegelrad-Erkennung hinzugefügt`
4. Auf **Commit & Push** klicken (kleiner Pfeil neben dem Commit-Button)

## Teil 8 — Projektstruktur verstehen

```
teamprojekt-ki-copilot/
│
├── src/                        ← Euer Python-Code (hier arbeiten)
│   ├── step_parser.py          STEP-Datei einlesen (Schritt 1)
│   ├── geometry_analyzer.py    Zahnrad-Parameter berechnen (Schritt 2)
│   └── output_schema.py        JSON-Struktur für Gruppe A
│
├── data/
│   └── examples/               Test-STEP-Dateien (nicht auf GitHub!)
│
├── output/                     Generierte JSONs (nicht auf GitHub!)
│
├── .vscode/
│   └── settings.json           VS Code Einstellungen (für alle gleich)
│
├── environment.yml             ← conda-Umgebung (NICHT verändern ohne Absprache)
├── Dockerfile                  Docker-Setup für später
├── .gitignore                  Was nicht auf GitHub kommt
└── README.md
```

> ⚠️ `data/` und `output/` sind in `.gitignore` — große CAD-Dateien und generierte JSONs kommen **nicht** ins GitHub-Repo.

---

## Teil 9 — Wenn jemand `environment.yml` ändert

Falls ein Teammitglied eine neue Library hinzufügt und `environment.yml` aktualisiert, müsst ihr eure lokale Umgebung updaten:

```bash
conda env update -f environment.yml --prune
```

Ihr werdet im wöchentlichen Meeting informiert wenn sich die Umgebung ändert.

---

## Häufige Probleme

**`conda: command not found` nach Installation:**
```bash
# Mac:
~/miniconda3/bin/conda init zsh
# Terminal neu starten
```

**`(base)` statt `(gear-copilot)` im Terminal:**
```bash
conda activate gear-copilot
```

**Rote Unterstreichungen bei `from OCC...` in VS Code:**
→ Python-Interpreter auf `gear-copilot` setzen (Teil 6)

**`git pull` schlägt fehl wegen lokaler Änderungen:**
```bash
git stash        # eigene Änderungen kurz zur Seite legen
git pull         # neuesten Stand holen
git stash pop    # eigene Änderungen wieder anwenden
```

**Merge-Konflikt (zwei Personen haben dieselbe Datei geändert):**
→ VS Code zeigt die Konflikte an — im wöchentlichen Meeting gemeinsam lösen, nicht alleine kämpfen!

---

## Schnellreferenz: Die wichtigsten Befehle

```bash
# Umgebung aktivieren (immer als erstes!)
conda activate gear-copilot

# Neuesten Stand holen
git pull

# Skript ausführen
python src/step_parser.py --input data/examples/zahnrad.stp

# Änderungen hochladen
git add .
git commit -m "Beschreibung"
git push

# Umgebung updaten (nach Änderung an environment.yml)
conda env update -f environment.yml --prune
```
---