"""
output_helpers.py – Darstellungsfunktionen für das Test-Notebook.

Alle Funktionen geben HTML-Blöcke über IPython.display aus.
Farbschema: schwarze Schrift (#1a1a1a) auf neutralen Grautönen –
keine Signalfarben, optimiert für lesbare Auswertung.
"""

from __future__ import annotations

import html as _html
import json
from pathlib import Path

from IPython.display import display, HTML

# ---------------------------------------------------------------------------
# Farbschema
# ---------------------------------------------------------------------------
_BG_A       = "#f5f5f5"   # Chunk-Hintergrund gerade
_BG_B       = "#ebebeb"   # Chunk-Hintergrund ungerade
_BG_HEADER  = "#e2e2e2"   # Spalten-Header / Titelzeile
_BG_META    = "#edf0f5"   # Metadaten-JSON-Block (minimaler Blauton)
_BG_EMPTY   = "#f5f0eb"   # Kein Metadatum gefunden (minimaler Warmton)
_BG_ABOVE   = "#eef3ee"   # Score >= Threshold (minimales Grün)
_BG_BELOW   = "#f5f5f5"   # Score < Threshold (neutral)
_BG_ANSWER  = "#f8f9fa"   # Antwort-Container
_BDR        = "#cccccc"   # Standardrahmen
_BDR_ABOVE  = "#5a8a5a"   # Rahmen Treffer
_BDR_HEAD   = "#999999"   # Rahmen Überschrift
_TEXT       = "#1a1a1a"   # Primärer Text
_TEXT_SEC   = "#555555"   # Sekundärer Text (Metazeile)
_ACCENT     = "#2255aa"   # Akzent für Scores / Labels


def _container(titel: str, n: int | None, inhalt: str, hoehe: int) -> str:
    zaehler = f'<span style="color:{_TEXT_SEC}; margin-left:8px;">({n} Einträge)</span>' if n is not None else ""
    return (
        f'<div style="border:1px solid {_BDR_HEAD}; border-radius:5px; padding:10px; margin:10px 0;">'
        f'<div style="background:{_BG_HEADER}; padding:5px 10px; border-radius:3px; margin-bottom:8px;">'
        f'<b style="color:{_TEXT};">{_html.escape(titel)}</b>{zaehler}</div>'
        f'<div style="max-height:{hoehe}px; overflow-y:auto; font-family:monospace; font-size:0.87em; line-height:1.5;">'
        f'{inhalt}'
        f'</div></div>'
    )


# ---------------------------------------------------------------------------
# Block 1 – Chunker: Statistik + Chunk-Volltext
# Evaluationsziel: semantische Kohärenz und Größenverteilung prüfen
# ---------------------------------------------------------------------------

def zeige_chunk_statistik(chunks) -> None:
    """
    Zeigt Kennzahlen zur Chunk-Verteilung: Anzahl, Wortgrößen, Chunks pro Seite.
    Ideal zur Überprüfung ob der SemanticChunker sinnvoll segmentiert hat.
    """
    woerter = [len(c.text.split()) for c in chunks]
    seiten: dict[int, int] = {}
    for c in chunks:
        seiten[c.page_number] = seiten.get(c.page_number, 0) + 1

    zeilen = []
    zeilen.append(
        f'<div style="display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin-bottom:10px;">'
    )
    for label, wert in [
        ("Chunks gesamt", str(len(chunks))),
        ("Ø Wörter", f"{sum(woerter)/len(woerter):.0f}"),
        ("Min Wörter", str(min(woerter))),
        ("Max Wörter", str(max(woerter))),
    ]:
        zeilen.append(
            f'<div style="background:{_BG_HEADER}; border:1px solid {_BDR}; border-radius:4px;'
            f'padding:8px 12px; text-align:center;">'
            f'<div style="font-size:1.3em; font-weight:bold; color:{_ACCENT};">{wert}</div>'
            f'<div style="color:{_TEXT_SEC}; font-size:0.85em;">{label}</div>'
            f'</div>'
        )
    zeilen.append("</div>")

    # Chunks pro Seite
    zeilen.append(f'<div style="color:{_TEXT_SEC}; font-size:0.9em; margin-bottom:6px;"><b>Chunks pro Seite:</b> ')
    zeilen.append(" | ".join(f"S.{s}: {n}" for s, n in sorted(seiten.items())))
    zeilen.append("</div>")

    # Größenverteilung als ASCII-Balken
    zeilen.append(f'<div style="margin-top:8px; font-family:monospace; font-size:0.86em;">')
    zeilen.append(f'<b>Größenverteilung (Wörter pro Chunk):</b><br>')
    grenzen = [(0,50),(50,100),(100,200),(200,300),(300,512),(512,9999)]
    labels  = ["  0– 50","50–100","100–200","200–300","300–512","512+   "]
    for (lo, hi), lbl in zip(grenzen, labels):
        n = sum(1 for w in woerter if lo <= w < hi)
        balken = "█" * n
        zeilen.append(f'{lbl}: {balken} ({n})<br>')
    zeilen.append("</div>")

    display(HTML("".join(zeilen)))


def zeige_satzaehnlichkeit_svg(
    dokument,
    embedder,
    threshold: float,
    min_chunk_tokens: int = 80,
    max_chunk_tokens: int = 512,
    overlap_sentences: int = 1,
    hoehe: int = 340,
) -> None:
    """
    SVG-Liniendiagramm: Kosinus-Ähnlichkeit zwischen benachbarten Sätzen.
    X-Achse: n-ter Satz, Y-Achse: Ähnlichkeit 0.0–1.0.

    Unterhalb der x-Achse: Chunk-Leiste mit einem farbigen Balken pro
    tatsächlich gewähltem Chunk (nach min/max-Token-Filter). Zwei alternierende
    Farben machen benachbarte Chunks sofort unterscheidbar. Semantische Grenzen
    (sim < threshold) erzeugen im Balken einen natürlichen Leerraum. Der Plot
    selbst bleibt weiß und unüberlagert.
    """
    import math as _math
    from app.implementations.text_split import split_sentences, approx_tokens

    _C1 = "#6baed6"   # Blau  – gerade Chunk-Indizes
    _C2 = "#74c476"   # Grün  – ungerade Chunk-Indizes

    def _cos(a: list, b: list) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = _math.sqrt(sum(x * x for x in a)) or 1.0
        nb = _math.sqrt(sum(y * y for y in b)) or 1.0
        return dot / (na * nb)

    # ── Daten sammeln ─────────────────────────────────────────────────────
    # sims[k]      = cos-Ähnlichkeit zwischen Satz k und k+1 (global)
    # chunk_spans  = Liste von (left_sim_idx, right_sim_idx) für jeden tatsächlich
    #                gewählten Chunk. Indizes sind float (±0.5 um den Mittelbereich
    #                des Chunks zu erfassen). Wird für die Chunk-Leiste genutzt.
    sims: list[float] = []
    chunk_spans: list[tuple[float, float]] = []
    page_starts: list[tuple[int, int]] = []

    for page in dokument.pages:
        sents = split_sentences(page.text)
        if len(sents) < 2:
            continue
        vecs = embedder.embed(sents).dense_vectors

        page_offset = len(sims)
        page_starts.append((page_offset, page.page_number))

        page_sims = [_cos(vecs[i - 1], vecs[i]) for i in range(1, len(sents))]

        # Semantische Segmentgrenzen
        boundaries: set[int] = set()
        for i in range(1, len(sents)):
            if page_sims[i - 1] < threshold:
                boundaries.add(i)

        cuts = [0] + sorted(boundaries) + [len(sents)]
        seg_ranges = list(zip(cuts, cuts[1:]))

        # pack_segment replizieren → Span jedes gültigen Sub-Chunks bestimmen
        for a, b in seg_ranges:
            seg = sents[a:b]
            start = 0
            while start < len(seg):
                cur_tokens, i = 0, start
                while i < len(seg):
                    t = approx_tokens(seg[i])
                    if i > start and (cur_tokens + t) > max_chunk_tokens:
                        break
                    cur_tokens += t
                    i += 1
                sub_text = " ".join(seg[start:i])
                if sub_text and approx_tokens(sub_text) >= min_chunk_tokens:
                    # Span in Sim-Space: von 0.5 vor erstem bis 0.5 nach letztem Sim
                    # des Sub-Chunks. Bei Einzelsatz: minimale Breite von 1.0.
                    left_idx  = float(page_offset + a + start) - 0.5
                    right_idx = float(page_offset + a + i - 2) + 0.5
                    if right_idx < left_idx:       # Einzelsatz-Chunk
                        right_idx = left_idx + 1.0
                    chunk_spans.append((left_idx, right_idx))
                start = max(i - overlap_sentences, start + 1)

        for s in page_sims:
            sims.append(s)

    if not sims:
        display(HTML(f'<p style="color:{_TEXT_SEC};">Keine Satzpaare vorhanden.</p>'))
        return

    N = len(sims)

    # ── Layout ────────────────────────────────────────────────────────────
    W = 820
    H = hoehe
    lm, rm, tm, bm = 54, 46, 40, 92   # bm erhöht: Chunk-Leiste + Legende unterhalb
    pw = W - lm - rm
    ph = H - tm - bm

    half_col = pw / max(N - 1, 1) / 2   # halbe Spaltenbreite je Datenpunkt

    def sx(i: float) -> float:
        return lm + (i / max(N - 1, 1)) * pw

    def sy(v: float) -> float:
        return tm + (1.0 - max(0.0, min(1.0, v))) * ph

    p: list[str] = []

    # ── SVG-Hintergrund ───────────────────────────────────────────────────
    p.append(
        f'<rect width="{W}" height="{H}" fill="{_BG_ANSWER}" '
        f'stroke="{_BDR}" stroke-width="1" rx="4"/>'
    )

    # ── Plotfläche: einheitlich weiß – Chunk-Info in eigener Leiste unterhalb ─
    p.append(
        f'<rect x="{lm}" y="{tm}" width="{pw}" height="{ph}" '
        f'fill="white" stroke="none"/>'
    )

    # ── Plotflächen-Rahmen ────────────────────────────────────────────────
    p.append(
        f'<rect x="{lm}" y="{tm}" width="{pw}" height="{ph}" '
        f'fill="none" stroke="{_BDR}" stroke-width="0.8"/>'
    )

    # ── Y-Achsen-Ticks + Beschriftung (kein Gitternetz) ───────────────────
    for tick in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
        y = sy(tick)
        p.append(
            f'<line x1="{lm - 4}" y1="{y:.1f}" x2="{lm}" y2="{y:.1f}" '
            f'stroke="{_TEXT}" stroke-width="1"/>'
        )
        p.append(
            f'<text x="{lm - 7}" y="{y + 3.5:.1f}" text-anchor="end" '
            f'font-size="10" fill="{_TEXT_SEC}">{tick:.1f}</text>'
        )

    # ── Seitengrenzen (senkrechte Linien) + Labels ÜBER oberer Kante ─────
    # Zentrierung der Labels auf den jeweiligen Seitenbereich
    for idx, (sim_start, page_num) in enumerate(page_starts):
        sim_end = (page_starts[idx + 1][0] - 1) if idx + 1 < len(page_starts) else N - 1
        center_x = sx((sim_start + sim_end) / 2.0)
        p.append(
            f'<text x="{center_x:.1f}" y="{tm - 7}" text-anchor="middle" '
            f'font-size="10" fill="{_TEXT_SEC}">S.{page_num}</text>'
        )
        # Seitenmarkierung: zwei Strichel oberhalb der oberen Kante (nicht im Plot)
        if idx > 0:
            xp = sx(sim_start - 0.5)
            p.append(
                f'<line x1="{xp:.1f}" y1="{tm - 14}" x2="{xp:.1f}" y2="{tm}" '
                f'stroke="{_TEXT_SEC}" stroke-width="1.5" stroke-dasharray="5,5"/>'
            )

    # ── Threshold-Linie ───────────────────────────────────────────────────
    yt = max(tm + 6, min(tm + ph - 6, sy(threshold)))   # y-Clamp verhindert Rand-Kollision
    p.append(
        f'<line x1="{lm}" y1="{yt:.1f}" x2="{lm + pw}" y2="{yt:.1f}" '
        f'stroke="{_ACCENT}" stroke-width="1.5" stroke-dasharray="7,4"/>'
    )
    p.append(
        f'<text x="{lm + pw + 5}" y="{yt + 4:.1f}" '
        f'font-size="10" fill="{_ACCENT}">τ={threshold}</text>'
    )

    # ── Datenlinie ────────────────────────────────────────────────────────
    pts = " ".join(f"{sx(i):.1f},{sy(s):.1f}" for i, s in enumerate(sims))
    p.append(
        f'<polyline points="{pts}" fill="none" stroke="{_TEXT}" '
        f'stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/>'
    )

    # ── Datenpunkte ───────────────────────────────────────────────────────
    for i, s in enumerate(sims):
        col = _BDR_ABOVE if s >= threshold else _ACCENT
        p.append(
            f'<circle cx="{sx(i):.1f}" cy="{sy(s):.1f}" r="3.5" '
            f'fill="{col}" stroke="white" stroke-width="1.2"/>'
        )

    # ── Achsen ────────────────────────────────────────────────────────────
    p.append(
        f'<line x1="{lm}" y1="{tm + ph}" x2="{lm + pw}" y2="{tm + ph}" '
        f'stroke="{_TEXT}" stroke-width="1.2"/>'
    )
    p.append(
        f'<line x1="{lm}" y1="{tm}" x2="{lm}" y2="{tm + ph}" '
        f'stroke="{_TEXT}" stroke-width="1.2"/>'
    )

    # ── X-Achsen-Ticks + Beschriftung ────────────────────────────────────
    step = max(1, N // 12)
    for i in range(0, N, step):
        x = sx(i)
        p.append(
            f'<line x1="{x:.1f}" y1="{tm + ph}" x2="{x:.1f}" y2="{tm + ph + 4}" '
            f'stroke="{_TEXT}" stroke-width="1"/>'
        )
        p.append(
            f'<text x="{x:.1f}" y="{tm + ph + 16}" text-anchor="middle" '
            f'font-size="10" fill="{_TEXT_SEC}">{i + 1}</text>'
        )

    # ── Chunk-Leiste ──────────────────────────────────────────────────────
    # Direkt unterhalb der x-Tick-Labels: ein farbiger Balken pro Chunk.
    # Zwei alternierende Farben (_C1/_C2) machen benachbarte Chunks
    # auf einen Blick unterscheidbar. Semantische Grenzen (sim < τ) erzeugen
    # einen natürlichen Leerraum, Seiten-/Token-Grenzen einen 1-px-Spalt.
    bar_y = tm + ph + 24
    bar_h = 10
    for c_idx, (left_idx, right_idx) in enumerate(chunk_spans):
        bx1 = max(lm, sx(left_idx)) + 1.0    # +1 px Abstand zum Vorgänger
        bx2 = min(lm + pw, sx(right_idx))
        if bx2 < bx1 + 2.0:
            bx2 = bx1 + 2.0                  # Mindestbreite
        col = _C1 if c_idx % 2 == 0 else _C2
        p.append(
            f'<rect x="{bx1:.1f}" y="{bar_y}" width="{bx2 - bx1:.1f}" '
            f'height="{bar_h}" fill="{col}" opacity="0.82" rx="1"/>'
        )
        # Chunk-Nummer mittig im Balken, wenn genug Platz
        if bx2 - bx1 >= 11:
            p.append(
                f'<text x="{(bx1 + bx2) / 2:.1f}" y="{bar_y + 7.5:.1f}" '
                f'text-anchor="middle" font-size="7.5" fill="white" '
                f'font-weight="bold">{c_idx + 1}</text>'
            )
    # Beschriftung links von der Leiste
    p.append(
        f'<text x="{lm - 5}" y="{bar_y + 7.5:.1f}" text-anchor="end" '
        f'font-size="9" fill="{_TEXT_SEC}">Chunks</text>'
    )

    # ── Achsenbeschriftungen ──────────────────────────────────────────────
    mid_x = lm + pw // 2
    mid_y = tm + ph // 2
    p.append(
        f'<text x="{mid_x}" y="{tm + ph + 46}" text-anchor="middle" '
        f'font-size="11" fill="{_TEXT_SEC}">n-ter Satz</text>'
    )
    p.append(
        f'<text x="12" y="{mid_y}" text-anchor="middle" font-size="11" '
        f'fill="{_TEXT_SEC}" transform="rotate(-90, 12, {mid_y})">'
        f'Kosinus-Ähnlichkeit</text>'
    )

    # ── Legende UNTERHALB des Diagramms ──────────────────────────────────
    ly = tm + ph + 70
    legend_items: list[tuple[str, str, str]] = [
        ("circle", _BDR_ABOVE, "≥ τ"),
        ("circle", _ACCENT,    "< τ"),
        ("chunk_bar", "",       "Chunk"),
    ]
    if len(page_starts) > 1:
        legend_items.append(("dash", _TEXT_SEC, "Seitengrenze"))

    item_w = 100
    total_w = len(legend_items) * item_w
    ix0 = lm + (pw - total_w) // 2

    for idx_l, (kind, color, label) in enumerate(legend_items):
        ix = ix0 + idx_l * item_w
        if kind == "circle":
            p.append(
                f'<circle cx="{ix + 7}" cy="{ly - 3}" r="5" '
                f'fill="{color}" stroke="white" stroke-width="1"/>'
            )
        elif kind == "chunk_bar":
            # Zwei Farben nebeneinander zeigen die Alternierung
            p.append(
                f'<rect x="{ix}" y="{ly - 9}" width="7" height="10" '
                f'fill="{_C1}" opacity="0.82" rx="1"/>'
            )
            p.append(
                f'<rect x="{ix + 8}" y="{ly - 9}" width="7" height="10" '
                f'fill="{_C2}" opacity="0.82" rx="1"/>'
            )
        elif kind == "dash":
            p.append(
                f'<line x1="{ix}" y1="{ly - 3}" x2="{ix + 14}" y2="{ly - 3}" '
                f'stroke="{color}" stroke-width="1.5" stroke-dasharray="4,3" opacity="0.7"/>'
            )
        p.append(
            f'<text x="{ix + 18}" y="{ly + 1}" font-size="10" fill="{_TEXT}">{label}</text>'
        )

    # ── SVG zusammenbauen ─────────────────────────────────────────────────
    svg = (
        f'<svg width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg" '
        f'style="font-family:sans-serif; display:block;">'
        + "".join(p)
        + "</svg>"
    )

    display(HTML(
        f'<div style="border:1px solid {_BDR_HEAD}; border-radius:5px; '
        f'padding:10px; margin:10px 0;">'
        f'<div style="background:{_BG_HEADER}; padding:5px 10px; border-radius:3px; '
        f'margin-bottom:8px;">'
        f'<b style="color:{_TEXT};">Satz-Ähnlichkeitsverlauf</b>'
        f'<span style="color:{_TEXT_SEC}; font-size:0.85em; margin-left:10px;">'
        f'({N} Satzpaare | Threshold={threshold})</span></div>'
        + svg
        + "</div>"
    ))


def zeige_chunks_html(chunks, titel="Chunks", hoehe=750) -> None:
    """
    Scrollbarer Container mit allen Chunks.
    Pro Chunk: Metazeile (Nummer, Seite, Wörter) + vollständiger Text.
    Evaluation: Prüfen ob Chunk-Grenzen semantisch sinnvoll gesetzt sind.
    """
    teile = []
    for i, chunk in enumerate(chunks):
        bg = _BG_A if i % 2 == 0 else _BG_B
        teile.append(
            f'<div style="background:{bg}; border-left:3px solid {_BDR_HEAD};'
            f'margin:4px 0; padding:7px 12px; border-radius:3px;">'
            f'<div style="color:{_TEXT_SEC}; font-size:0.83em; margin-bottom:3px;">'
            f'<b style="color:{_ACCENT};">Chunk {i+1}</b>'
            f' &nbsp;|&nbsp; Seite {chunk.page_number}'
            f' &nbsp;|&nbsp; Pos {chunk.position}'
            f' &nbsp;|&nbsp; {len(chunk.text.split())} Wörter'
            f'</div>'
            f'<div style="color:{_TEXT}; white-space:pre-wrap; word-break:break-word;">'
            f'{_html.escape(chunk.text)}</div>'
            f'</div>'
        )
    display(HTML(_container(titel, len(chunks), "".join(teile), hoehe)))


# ---------------------------------------------------------------------------
# Block 2 – Metadaten-Extraktor: Befüllungsrate + Detailansicht
# Evaluationsziel: prüfen ob LLM die richtigen Felder je Chunk erkennt
# ---------------------------------------------------------------------------

def zeige_metadaten_befuellung(metadata_liste: list[dict], schema_felder: list[str]) -> None:
    """
    ASCII-Balkentabelle: wie oft wurde jedes Schema-Feld befüllt?
    Evaluation: sofort erkennbar welche Felder das LLM zuverlässig extrahiert.
    """
    n = len(metadata_liste)
    counts = {f: 0 for f in schema_felder}
    for meta in metadata_liste:
        for k, v in meta.items():
            if k in counts and v is not None and v not in ("unspecified", ""):
                counts[k] += 1

    zeilen = [f'<div style="font-family:monospace; font-size:0.88em; line-height:1.8;">']
    zeilen.append(f'<b>Feld-Befüllungsrate</b> ({n} Chunks):<br>')
    for feld, anzahl in sorted(counts.items(), key=lambda x: -x[1]):
        rate = anzahl / n * 100 if n else 0
        gefuellt = int(rate / 5)
        leer = 20 - gefuellt
        balken = f'<span style="color:{_ACCENT};">{"█" * gefuellt}</span>{"░" * leer}'
        zeilen.append(
            f'<span style="display:inline-block; width:160px;">{feld}</span>'
            f'{balken} &nbsp; {anzahl}/{n} ({rate:.0f}%)<br>'
        )
    zeilen.append("</div>")
    display(HTML("".join(zeilen)))


def zeige_metadaten_html(chunks, metadata_liste: list[dict], hoehe=650) -> None:
    """
    Pro Chunk: Textvorschau (erste 180 Zeichen) + extrahierte Metadaten als JSON.
    Grün-tönig wenn Felder gefunden, warm-neutral wenn leer.
    Evaluation: Qualitätskontrolle der LLM-Extraktion pro Chunk.
    """
    teile = []
    for i, (chunk, meta) in enumerate(zip(chunks, metadata_liste)):
        non_null = {k: v for k, v in meta.items()
                    if v is not None and v not in ("unspecified", "")}
        bg_meta = "#edf2f7" if non_null else "#f5f5f5"   # dezentes Blaugrau / Hellgrau
        meta_str = json.dumps(non_null, ensure_ascii=False, indent=2) if non_null else "(keine Felder extrahiert)"
        vorschau = chunk.text[:180].replace("\n", " ") + ("…" if len(chunk.text) > 180 else "")
        teile.append(
            f'<div style="border:1px solid {_BDR}; margin:5px 0; border-radius:3px; overflow:hidden;">'
            f'<div style="background:{_BG_HEADER}; padding:4px 10px; font-size:0.83em; color:{_TEXT};">'
            f'<b>Chunk {i+1}</b> &nbsp;|&nbsp; Seite {chunk.page_number}'
            f' &nbsp;|&nbsp; {len(chunk.text.split())} Wörter</div>'
            f'<div style="background:#fafafa; padding:6px 10px; color:{_TEXT}; font-size:0.84em;">'
            f'{_html.escape(vorschau)}</div>'
            f'<div style="background:{bg_meta}; padding:6px 10px; white-space:pre; font-size:0.85em;'
            f'color:{_TEXT};">{_html.escape(meta_str)}</div>'
            f'</div>'
        )
    display(HTML(_container("Extrahierte Metadaten pro Chunk", len(chunks), "".join(teile), hoehe)))


# ---------------------------------------------------------------------------
# Block 3 – Kosinus-Ähnlichkeit: sortiertes Ranking pro Frage
# Evaluationsziel: prüfen ob semantisch relevante Chunks hoch ranken
# ---------------------------------------------------------------------------

def zeige_aehnlichkeit_html(frage: str, chunk_scores: list, threshold: float, hoehe=480) -> None:
    """
    Sortiertes Ranking aller Chunks zur Frage mit Score und Balken.
    Grün-tönig >= threshold, neutral darunter. Threshold-Linie sichtbar.
    Evaluation: zeigt ob der Embedder die richtigen Chunks an die Spitze setzt.
    """
    oberhalb = sum(1 for s, _ in chunk_scores if s >= threshold)
    teile = []
    threshold_gezeigt = False

    for rank, (score, chunk) in enumerate(chunk_scores, 1):
        if not threshold_gezeigt and score < threshold:
            teile.append(
                f'<div style="border-top:2px dashed {_BDR_HEAD}; margin:4px 0;'
                f'text-align:center; color:{_TEXT_SEC}; font-size:0.82em; padding:2px 0;">'
                f'── Threshold {threshold:.2f} ──</div>'
            )
            threshold_gezeigt = True

        bg = _BG_ABOVE if score >= threshold else _BG_BELOW
        bdr = _BDR_ABOVE if score >= threshold else _BDR
        balken_w = max(2, int(score * 160))
        vorschau = chunk.text[:200].replace("\n", " ") + ("…" if len(chunk.text) > 200 else "")
        teile.append(
            f'<div style="background:{bg}; border:1px solid {bdr}; margin:3px 0;'
            f'padding:6px 10px; border-radius:3px;">'
            f'<div style="margin-bottom:3px; color:{_TEXT_SEC}; font-size:0.83em;">'
            f'<b style="color:{_ACCENT};">#{rank}</b>'
            f' &nbsp; Score: <b style="color:{_TEXT};">{score:.4f}</b>'
            f' &nbsp;|&nbsp; Seite {chunk.page_number}'
            f' &nbsp;|&nbsp; Pos {chunk.position}'
            f'<span style="display:inline-block; width:{balken_w}px; height:7px;'
            f'background:{_ACCENT}; border-radius:2px; margin-left:12px; vertical-align:middle;"></span>'
            f'</div>'
            f'<div style="color:{_TEXT}; font-size:0.85em;">{_html.escape(vorschau)}</div>'
            f'</div>'
        )
    if not threshold_gezeigt:
        teile.append(
            f'<div style="border-top:2px dashed {_BDR_HEAD}; margin:4px 0;'
            f'color:{_TEXT_SEC}; font-size:0.82em; text-align:center; padding:2px 0;">'
            f'── alle Chunks >= Threshold {threshold:.2f} ──</div>'
        )

    header = (
        f'<div style="margin-bottom:6px; font-size:0.9em;">'
        f'<b>Frage:</b> {_html.escape(frage)}<br>'
        f'<span style="color:{_TEXT_SEC};">{oberhalb} von {len(chunk_scores)} Chunks '
        f'&ge; Threshold {threshold:.2f}</span></div>'
    )
    display(HTML(_container("Kosinus-Ähnlichkeit", None, header + "".join(teile), hoehe)))


# ---------------------------------------------------------------------------
# Block 4 – Retriever: Filter-Bedingungen + Ergebnisse
# Evaluationsziel: prüfen ob Stage-1-Filter korrekt greift und Stage-2 relevante Chunks liefert
# ---------------------------------------------------------------------------

def zeige_retrieval_html(frage: str, retrieved_chunks, filter_bedingungen: dict | None,
                         hoehe=580) -> None:
    """
    Zeigt Stage-1-Filterbedingungen und Stage-2-Ergebnisse mit Score, Metadaten, Text.
    Evaluation: Verifikation des zweistufigen Retriever-Verhaltens.
    """
    teile = []

    # Stage-1-Filter
    if filter_bedingungen and filter_bedingungen.get("must"):
        filter_json = json.dumps(filter_bedingungen, ensure_ascii=False, indent=2)
        teile.append(
            f'<div style="background:#edf2f7; border:1px solid {_BDR}; border-radius:3px;'
            f'padding:6px 10px; margin-bottom:8px;">'
            f'<b style="font-size:0.88em; color:{_TEXT};">Stage-1-Filter ({len(filter_bedingungen["must"])} Bedingungen):</b>'
            f'<pre style="margin:4px 0 0 0; font-size:0.82em; color:{_TEXT};">{_html.escape(filter_json)}</pre>'
            f'</div>'
        )
    else:
        teile.append(
            f'<div style="background:{_BG_HEADER}; border:1px solid {_BDR}; border-radius:3px;'
            f'padding:5px 10px; margin-bottom:8px; color:{_TEXT}; font-size:0.88em;">'
            f'Stage-1-Filter: (keine Bedingungen – kein passender Kontext)</div>'
        )

    teile.append(
        f'<div style="color:{_TEXT}; font-size:0.88em; margin-bottom:6px;">'
        f'<b>Frage:</b> {_html.escape(frage)} &nbsp;|&nbsp; {len(retrieved_chunks)} Treffer</div>'
    )

    for i, rc in enumerate(retrieved_chunks):
        non_null = {k: v for k, v in rc.metadata.items()
                    if v is not None and v not in ("unspecified", "")}
        meta_json = json.dumps(non_null, ensure_ascii=False) if non_null else "(keine Metadaten)"
        chunk_name = Path(rc.chunk.source_path).name
        teile.append(
            f'<div style="border:1px solid {_BDR}; margin:5px 0; border-radius:3px; overflow:hidden;">'
            f'<div style="background:{_BG_HEADER}; padding:4px 10px; font-size:0.84em; color:{_TEXT};">'
            f'<b style="color:{_ACCENT};">[Q{i+1}]</b>'
            f' Score: <b>{rc.similarity:.4f}</b>'
            f' &nbsp;|&nbsp; Seite {rc.chunk.page_number}'
            f' &nbsp;|&nbsp; {_html.escape(chunk_name)}</div>'
            f'<div style="background:#edf2f7; padding:4px 10px; font-size:0.83em;'
            f'white-space:pre; color:{_TEXT};">{_html.escape(meta_json)}</div>'
            f'<div style="background:#fafafa; padding:6px 10px; color:{_TEXT}; white-space:pre-wrap;'
            f'word-break:break-word; font-size:0.86em;">{_html.escape(rc.chunk.text)}</div>'
            f'</div>'
        )
    display(HTML(_container("Retrieval-Ergebnis", None, "".join(teile), hoehe)))


# ---------------------------------------------------------------------------
# Block 5 – Antwortgenerierung
# Evaluationsziel: Quellenverweise, Faktentreue, Formatkonformität prüfen
# ---------------------------------------------------------------------------

def zeige_antwort_html(frage: str, antwort: dict, cad_kontext: dict | None = None) -> None:
    """
    Antworttext mit expandierbaren Quellen und CAD-Kontext-Übersicht.
    Evaluation: prüfen ob [Q1]-Verweise korrekt gesetzt und Fakten belegbar sind.
    """
    # CAD-Kontext
    cad_html = ""
    if cad_kontext:
        cad_str = json.dumps(cad_kontext, ensure_ascii=False)
        cad_html = (
            f'<div style="background:{_BG_HEADER}; border:1px solid {_BDR}; border-radius:3px;'
            f'padding:5px 10px; margin-bottom:8px; font-size:0.84em; color:{_TEXT_SEC};">'
            f'<b>CAD-Kontext:</b> {_html.escape(cad_str)}</div>'
        )

    # Antworttext – [Qx]-Verweise fett hervorheben
    antwort_text = _html.escape(antwort.get("answer_text", ""))
    import re as _re
    antwort_text = _re.sub(
        r'(\[Q\d+\])',
        rf'<b style="color:{_ACCENT};">\1</b>',
        antwort_text
    )

    # Quellen
    quellen_html = ""
    sources = antwort.get("sources", [])
    if sources:
        rows = "".join(
            f'<tr style="background:{"" if i%2==0 else _BG_A};">'
            f'<td style="padding:4px 8px; color:{_ACCENT};"><b>[{s["qid"]}]</b></td>'
            f'<td style="padding:4px 8px;">{_html.escape(Path(s["source_path"]).name)}</td>'
            f'<td style="padding:4px 8px; text-align:center;">S.{s["page_number"]}</td>'
            f'<td style="padding:4px 8px; text-align:right;">{s["similarity"]:.4f}</td>'
            f'</tr>'
            for i, s in enumerate(sources)
        )
        quellen_html = (
            f'<details style="margin-top:8px;">'
            f'<summary style="cursor:pointer; color:{_TEXT_SEC}; font-size:0.88em;">'
            f'<b>Quellen ({len(sources)})</b></summary>'
            f'<table style="width:100%; border-collapse:collapse; font-size:0.85em;'
            f'margin-top:6px; font-family:monospace;">'
            f'<tr style="background:{_BG_HEADER};">'
            f'<th style="padding:4px 8px; text-align:left;">Ref</th>'
            f'<th style="padding:4px 8px; text-align:left;">Datei</th>'
            f'<th style="padding:4px 8px;">Seite</th>'
            f'<th style="padding:4px 8px; text-align:right;">Score</th></tr>'
            f'{rows}</table></details>'
        )

    teile = [
        f'<div style="background:{_BG_A}; border:1px solid {_BDR}; border-radius:3px;'
        f'padding:6px 10px; margin-bottom:8px; font-size:0.92em; color:{_TEXT};">'
        f'<b>Frage:</b> {_html.escape(frage)}</div>',
        cad_html,
        f'<div style="background:{_BG_ANSWER}; border:1px solid {_BDR}; border-radius:3px;'
        f'padding:10px 14px; color:{_TEXT}; white-space:pre-wrap; line-height:1.65;'
        f'font-size:0.92em;">{antwort_text}</div>',
        quellen_html,
    ]
    display(HTML(_container("Generierte Antwort", None, "".join(teile), 600)))
