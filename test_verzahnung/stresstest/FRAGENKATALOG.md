# Stresstest: Fragenkatalog mit Soll-Ergebnissen

Zwei Testdateien, die den Algorithmus gezielt an bekannte Grenzen bringen:

| Datei | Kanal | Upload-Ort |
|---|---|---|
| `stress_stueckliste_wissensbasis.csv` | Wissensbasis (TabularLoader → Retrieval → Tabellen-Filter/LLM) | Dokumentbibliothek |
| `stress_bauteil_geometrie.csv` | Bauteildaten (csv_gear_mapper → GearParameters) | Bauteil-Upload |

Eingebaute Stressfaktoren der Stückliste: **47 Zeilen** (mehr als `auto_table_context_rows: 40` –
Tabellen-Route 2 greift nicht mehr!), verwechselbare Werkstoffe (16MnCr5 / 16MnCrS5 / 20MnCr5,
42CrMo4 / 42CrMoS4, C45 / C45E), Teilstring-Bezeichnungen („Welle" ⊂ „Antriebswelle"),
Zahl 24 gleichzeitig als Menge und Zähnezahl, deutsche Dezimalkommas („1,5"), Kommas/Semikolons/
Klammern in Zellwerten, Leerwerte (`-`, `n/a`).

## Teil A: Wissensbasis-Fragen

Soll-Werkstoffverteilung als Referenz: 16MnCr5 = 7 (G-001, G-002, G-007, G-008, G-010, W-104, W-105) ·
42CrMo4 = 4 (G-004, G-012, W-101, W-103) · C45E = 4 · 100Cr6 = 5 · Stahl 8.8 = 3 · A2-70 = 2 ·
FKM = 2 · NBR = 2 · EN-GJL-250 = 2 · je 1× 16MnCrS5, 42CrMoS4, C45, 100CrMn6, 31CrMoV9.

### A1 – Muss vollständig funktionieren (deterministischer Tabellen-Filter)

| # | Frage | Soll | Prüft |
|---|---|---|---|
| 1 | Liste alle Bauteile aus 16MnCr5 auf | **7 Treffer** (s.o.), „Gesamt: 7" | Signalwort-Route 1 + Filter; 16MnCrS5/20MnCr5 dürfen NICHT erscheinen |
| 2 | Liste alle Bauteile aus 42CrMo4 auf | **4 Treffer**; W-108 (42CrMoS4) NICHT dabei | Exaktes Matching bei Suffix-Werkstoffen |
| 3 | Liste alle Bauteile aus C45 auf | **nur W-102** – keines der 4 C45E-Teile | Wortgrenzen-Matching (C45 ≠ C45E) |
| 4 | Wie viele Lager sind aus 100Cr6? | **5** (L-201, L-202, L-203, L-205, L-206); L-204 (100CrMn6) nicht | Zählfrage + Lookalike |
| 5 | Zeige alle Bauteile mit Menge 24 | **3** (S-501, S-503, S-507) – NICHT G-001/G-006 (Zähnezahl 24!) | Spalten-exakte Zahlenfilter |
| 6 | Welchen Werkstoff hat W-108? | 42CrMoS4 | ID-Einzelfakt, Zielspalten-Erkennung |
| 7 | Welche Oberflächenhärte hat G-003? | 60 HRC | Umlaut-Spaltenname als Zielspalte |
| 8 | Liste alle Bauteile nach DIN 912 auf | **2** (S-501, S-502) | Filter über Norm-Spalte |
| 9 | Liste alle Bauteile aus FKM auf | **2** (D-302, D-303) | Klammer-Wert „Dichtung (FKM) Deckel" darf Parsing nicht stören |

### A2 – Bekannte Grenzen (hier werden Schwächen erwartet – dokumentieren!)

| # | Frage | Erwartetes Verhalten / Schwäche |
|---|---|---|
| 10 | **Welche Bauteile bestehen aus 16MnCr5?** (ohne Listen-Signalwort) | Tabelle hat 47 Zeilen > `auto_table_context_rows: 40` → Route 2 lädt NICHT die ganze Tabelle. Der Filter sieht nur die top_k=5 Retrieval-Treffer → vermutlich **unvollständig** (nicht 7). Gegenprobe: Frage 1 formuliert mit „alle" liefert 7. **Fix-Kandidat:** `auto_table_context_rows` erhöhen oder „welche" in die Signalwörter aufnehmen. |
| 11 | Welche Bauteile haben 24 Zähne? | Geht an das LLM: „Zähne" ≠ Spaltenname „Zaehnezahl", daher blockt der Zahlen-Schutz den Filter. Soll wäre G-001 + G-006. LLM-Antwort auf Vollständigkeit prüfen. |
| 12 | Welche Bauteile sind angelassen? | Geht ans LLM. Zusatzfalle: Bei G-007 steht „einsatzgehärtet; angelassen" – das Semikolon im Zellwert kollidiert mit dem Feld-Trennzeichen der Satzform. Prüfen, ob G-007 gefunden wird. |
| 13 | Welche Werkstoffe kommen in der Stückliste vor? | Aggregation ohne konkreten Zellwert → LLM muss über viele Zeilen abstrahieren. Bei „welche" (kein Signalwort) zusätzlich Retrieval-Limit wie #10. Soll: 20 verschiedene Werkstoffe. |
| 14 | Welche Bezeichnung hat die Welle? | Mehrdeutig: „Welle" ist exakter Zellwert von W-102, aber 8 Bauteile sind Wellen. Der Filter antwortet strikt mit W-102 – fachlich vertretbar, aber Nutzererwartung dokumentieren. |
| 15 | Was bedeutet die Angabe 16MnCr5? | Muss ans LLM gehen (Erklärfrage, kein Filter-Hijack). Ohne Fachdokument in der Wissensbasis sollte das System sauber sagen, dass die Quellen dazu nichts hergeben – nicht halluzinieren. |
| 16 | Wie viel Getriebeöl wird benötigt? | Menge „1,5" (deutsches Komma) + Einheit steckt in Bemerkung („Liter"). Prüfen, ob die Antwort „1,5 Liter" zusammensetzt. |

## Teil B: Geometrie-CSV (Bauteildaten-Kanal)

`stress_bauteil_geometrie.csv` – Semikolon-getrennt, gemischte deutsche/englische/Kurzzeichen-Header,
Dezimalkommas, Einheiten in Zellen („2,75 mm", „20°"), eine Vorlagen-Zeile ohne Werte, zwei Bauteil-Zeilen.

**Soll nach Upload (verifiziert gegen csv_gear_mapper):**

- Zeile „INFO/Vorlage" wird übersprungen, **ZR-2044-B** (Zeile 3) wird das Bauteil
- `gear_type` = helical (aus Freitext „Schrägstirnrad")
- Modul 2,75 mm · 38 Zähne · Eingriffswinkel 20° · Schrägungswinkel 15,5° · Profilverschiebung +0,25
- d = 104,5 · da = 111,2 · df = 97,9 · b = 42 (Kurzzeichen-Header d/da/df/b)
- Werkstoff 18CrNiMo7-6 · Härte 60 HRC · Qualität 6
- Zwei Warnungen: „3 Datenzeilen …" und „Nicht zugeordnete Spalten: Schmierstoff, Zeichnungs-Nr"

**Gezielt eingebaute Schwächen-Probes:**

1. **Keine Plausibilitätsprüfung:** da = 111,2 ist theoretisch inkonsistent
   (d + 2·m·(1+x) = 104,5 + 5,5·1,25 ≈ 111,4). Das System übernimmt den Wert
   unkommentiert mit confidence 0.92 – prüfen, ob das irgendwo auffällt.
2. **Zweite Bauteilzeile (ZR-2045-A) wird stillschweigend ignoriert** – nur als
   Warnung sichtbar. Erscheint die Warnung im Frontend?
3. Anschlussfragen im Ask-Dialog stellen: „Welches Modul hat das Bauteil?" (Soll: 2,75 mm [CAD]),
   „Um welches Zahnrad handelt es sich?" (Soll: Schrägverzahnung, deterministischer CAD-Fast-Path),
   „Passt das Ritzel ZR-2045-A dazu?" (Soll: nicht im CAD-Kontext – sauberer Umgang prüfen).

## Auswertung

Für jede Frage notieren: vollständig / unvollständig / falsch / abgelehnt, plus ob der
Prozess-Trace den erwarteten Pfad zeigt („Tabellen-Filter" vs. Solver/Reviewer, und unter
„Chunk-Suche" ob die Tabelle vollständig geladen wurde). Die A2-Fälle sind die eigentliche
Ausbeute des Stresstests – das sind die Kandidaten für die nächste Verbesserungsrunde.
