"""
retriever_hybrid.py – Einstufiger Hybrid-Retriever (Dense + lexikalisch Sparse).

Bettet die Suchanfrage ein und sucht in Qdrant die semantisch ähnlichsten Chunks
via Kosinus-Ähnlichkeit. Bei use_hybrid=True wird der Dense-Score mit einem
lexikalischen Sparse-Score (Bag-of-words) gewichtet kombiniert – das verbessert
Treffer für Normnummern, Werkstoffbezeichnungen und technische Kurzbegriffe.

Tabellen-Threshold: Embeddings von Tabellenzeilen erzielen systembedingt
niedrigere Scores als Fließtext. Chunks aus Tabellen-Dokumenten
(doc_kind == "table") werden deshalb gegen table_min_similarity geprüft,
PDF-/Textchunks unverändert gegen min_similarity.

Split-Search-Routing (hebt die starre top_k-Grenze für Tabellen auf):
  Route 1 – Signalwörter: Listen-/Aggregatfragen („zeige alle Wellen",
    „wie viele Lager …") laden die bestplatzierte Tabelle komplett
    (gedeckelt auf aggregate_max_chunks).
  Route 2 – ergebnisgetrieben: Stammt die Mehrheit der Top-Treffer aus
    derselben Tabelle („die Frage landet breit in einer Tabelle"), wird diese
    auch OHNE Signalwort komplett geladen – sofern sie höchstens
    auto_table_context_rows Zeilen hat. So funktionieren auch Formulierungen
    ohne Schlüsselwort („Welche Wellen gibt es?") zuverlässig.

Beide Routen sind deterministisch (kein LLM-Call). Das Retrieval arbeitet
ausschließlich mit der Nutzerfrage; die CAD-Parameter fließen erst in der
Antwortstufe (AnswerGenerator) als Kontext ein.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from pathlib import Path
from typing import Callable, Optional

from app.core.interfaces import Embedder, VectorStore
from app.core.types import RetrievedChunk, SearchResult

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str], None]


def _notify(cb: Optional[ProgressCallback], event: str, detail: Optional[str] = None) -> None:
    """
    Meldet ein Prozessereignis, optional mit Detailtext (Nachvollziehbarkeit im GUI).
    Ältere Callbacks mit Ein-Argument-Signatur werden per TypeError-Fallback bedient.
    """
    if cb is None:
        return
    try:
        cb(event, detail)
    except TypeError:
        cb(event)

# Deutsche Signalwörter für Aggregat-/Listenfragen. Wortgrenzen verhindern
# Fehltreffer in Komposita ("Metalle" enthält kein \balle\b).
_AGGREGATE_RE = re.compile(
    r"\b("
    r"alle[nrs]?|s[äa]mtliche[nr]?|liste|auflist\w*|aufz[äa]hl\w*|auflistung|"
    r"[üu]bersicht|wie ?viele|anzahl|gesamt\w*|jede[nmrs]?|vollst[äa]ndig\w*|komplett\w*"
    r")\b",
    re.IGNORECASE,
)


def is_aggregate_query(question: str) -> bool:
    """True, wenn die Frage nach einer Auflistung/Gesamtmenge klingt statt nach einem Einzelfakt."""
    return bool(_AGGREGATE_RE.search(question or ""))


def _is_table_hit(hit: SearchResult) -> bool:
    return hit.metadata.get("doc_kind") == "table"


# Literaturverzeichnis-Seiten aus Lehrbüchern (z.B. "[PETE04] PETER, A.: …") ranken
# lexikalisch hoch, enthalten aber kein nutzbares Fachwissen – nur Fundstellen. Als
# LLM-Kontext sind sie giftig: Kleine Modelle spinnen aus Titeln im Verzeichnis
# scheinbare Empfehlungen (real passiert: "Innenhochdruck-Umformen" aus dem
# Klocke-Literaturverzeichnis wurde zur Fertigungsempfehlung "HPU" für Kegelräder).
# Heuristik: ≥3 Zitationsschlüssel im Klocke-/Springer-Stil ([ABCD04], [Pisc95a]).
_BIB_KEY_RE = re.compile(r"\[[A-ZÄÖÜ][A-Za-zÄÖÜäöü]{1,6}\d{2}[a-z]?\]")


def _is_bibliography_chunk(text: str) -> bool:
    """True für Chunks, die (überwiegend) Literaturverzeichnis sind – kein Wissenskontext."""
    return len(_BIB_KEY_RE.findall(text or "")) >= 3


class HybridRetriever:
    """Semantische Vektorsuche mit optionalem Hybrid-Scoring. Zustandslos bis auf injizierte Komponenten."""

    def __init__(
        self,
        *,
        embedder: Embedder,
        store: VectorStore,
        top_k: int,
        min_similarity: float,
        table_min_similarity: Optional[float] = None,
        use_hybrid: bool = True,
        hybrid_dense_weight: float = 0.7,
        hybrid_sparse_weight: float = 0.3,
        candidate_multiplier: int = 8,
        aggregate_max_chunks: int = 150,
        auto_table_context_rows: int = 40,
    ) -> None:
        """
        embedder muss dieselbe Instanz wie beim Indexieren sein (gleicher Vektorraum).
        candidate_multiplier: bei Hybrid-Suche werden top_k * multiplier Dense-Kandidaten
        geholt, lokal mit Sparse-Scores nachsortiert und auf top_k gekürzt.
        table_min_similarity: Threshold für Tabellenzeilen (None = wie min_similarity).
        aggregate_max_chunks: Deckel für Route 1 (Signalwörter).
        auto_table_context_rows: Maximalgröße einer Tabelle für Route 2 (0 = Route 2 aus).
        """
        self.embedder = embedder
        self.store = store
        self.top_k = top_k
        self.min_similarity = min_similarity
        self.table_min_similarity = min_similarity if table_min_similarity is None else table_min_similarity
        self.use_hybrid = use_hybrid
        self.hybrid_dense_weight = hybrid_dense_weight
        self.hybrid_sparse_weight = hybrid_sparse_weight
        self.candidate_multiplier = max(1, candidate_multiplier)
        self.aggregate_max_chunks = max(1, aggregate_max_chunks)
        self.auto_table_context_rows = max(0, auto_table_context_rows)

    def retrieve(
        self,
        question: str,
        progress_callback: Optional[ProgressCallback] = None,
        context_terms: Optional[str] = None,
    ) -> list[RetrievedChunk]:
        """
        Bettet die Suchanfrage ein und gibt die top_k ähnlichsten Chunks zurück.

        context_terms (optional): Bauteilkontext-Begriffe (z. B. „Kegelrad
        Kegelradverzahnung" aus app/core/cad_terms.py bei geladenem CAD-Bauteil).
        Sie werden NUR der Einbettungs-/Sparse-Query angehängt, damit bauteil-
        spezifische Literatur vor thematisch ähnlichen, aber bauteilfremden
        Treffern rankt. Listen-/Aggregatfragen bleiben unangereichert – dort
        soll das Tabellen-Routing allein von der Originalfrage gesteuert werden.
        """
        enriched = bool(context_terms) and not is_aggregate_query(question)
        query_text = f"{question}\n{context_terms}" if enriched else question

        _notify(progress_callback, "embedding_start")
        embedding = self.embedder.embed([query_text])
        _notify(progress_callback, "embedding_done")
        qvec = embedding.dense_vectors[0]
        qsparse = embedding.sparse_vectors[0] if embedding.sparse_vectors else None

        candidate_k = self.top_k * self.candidate_multiplier if self.use_hybrid else self.top_k

        _notify(progress_callback, "search_start")
        # Grober Vorfilter in Qdrant mit dem NIEDRIGEREN der beiden Thresholds –
        # sonst würden Tabellenzeilen serverseitig verworfen, bevor der
        # Kind-spezifische Filter unten greifen kann. Qdrant filtert hier auf den
        # DENSE-Kosinus-Score (der Vektorindex kennt nur den dichten Vektor).
        hits = self.store.search(
            qvec,
            top_k=candidate_k,
            threshold=min(self.min_similarity, self.table_min_similarity),
            query_sparse_vector=qsparse,
            use_hybrid=self.use_hybrid,
            hybrid_dense_weight=self.hybrid_dense_weight,
            hybrid_sparse_weight=self.hybrid_sparse_weight,
        )
        # Kind-spezifischer Relevanz-Threshold. WICHTIG: gegatet wird auf die
        # DICHTE Kosinus-Ähnlichkeit (dense_score, interpretierbar in [0,1]) –
        # NICHT auf den fusionierten Hybrid-Score. Der Hybrid-Score ist
        # 0.7·dense + 0.3·sparse; er wird bewusst nur zum RANKING (Sortierung)
        # verwendet. Würde man direkt gegen ihn schwellen, drückt allein das
        # Dense-Gewicht 0.7 selbst einen perfekten Treffer (1.0) auf 0.7, und
        # da BGE-M3-Sparse-Scores für kurze Fragen klein sind (~0.1–0.3), läge
        # die effektive Dense-Hürde bei ~0.71 – praktisch nichts käme durch
        # ("immer keine Chunks gefunden"). Der Hybrid-Score darf einen Treffer
        # zusätzlich RETTEN (max(...)), wenn ein starker lexikalischer Sparse-
        # Match (z.B. Normnummer „DIN 3990") den fusionierten Score über die
        # Schwelle hebt, obwohl der Dense-Score knapp darunter liegt.
        hits = [
            h for h in hits
            if max(h.dense_score if h.dense_score is not None else h.score, h.score)
            >= (self.table_min_similarity if _is_table_hit(h) else self.min_similarity)
        ]

        # Literaturverzeichnis-Chunks aussortieren (kein Wissenskontext, s. Heuristik oben).
        bib_dropped = sum(1 for h in hits if _is_bibliography_chunk(h.chunk.text))
        if bib_dropped:
            hits = [h for h in hits if not _is_bibliography_chunk(h.chunk.text)]

        routed = self._route_table_context(question, hits)
        if routed is not None:
            chunks, route = routed
        else:
            chunks = [
                RetrievedChunk(chunk=h.chunk, metadata=h.metadata, similarity=h.score)
                for h in hits[: self.top_k]
            ]
            route = None

        # Detailtext für den Prozess-Schritt "Chunk-Suche": welche Dateien,
        # welche Seiten/Zeilen, welche Route – macht das Retrieval im GUI prüfbar.
        detail = self._search_detail(chunks, route)
        if bib_dropped:
            detail += f" · {bib_dropped} Literaturverzeichnis-Auszug/-Auszüge verworfen."
        if enriched:
            detail += f" · Suche um Bauteilkontext erweitert ({context_terms})."
        _notify(progress_callback, "search_done", detail)
        return chunks

    # ------------------------------------------------------------------
    # Split-Search-Routing
    # ------------------------------------------------------------------

    def _route_table_context(self, question: str, hits: list[SearchResult]) -> Optional[tuple[list[RetrievedChunk], str]]:
        """
        Entscheidet deterministisch, ob statt der top_k-Treffer eine ganze Tabelle
        als Kontext geladen wird. Gibt (Chunks, Routenname) zurück – oder None,
        wenn der normale Pfad greifen soll.
        """
        if not hits:
            return None
        scroll = getattr(self.store, "scroll_by_doc_hash", None)
        if scroll is None:  # VectorStore-Implementierung ohne Scroll-Unterstützung
            return None

        # Route 1 – Signalwörter: bestplatzierter Tabellen-Treffer unter ALLEN
        # Kandidaten wird expandiert (hits sind score-sortiert).
        if is_aggregate_query(question):
            seed = next((h for h in hits if _is_table_hit(h)), None)
            if seed is not None:
                rows = scroll(seed.chunk.doc_hash, limit=self.aggregate_max_chunks)
                if rows:
                    return self._as_table_context(rows, seed, route="keyword")

        # Route 2 – ergebnisgetrieben: Mehrheit der top_k-Treffer aus derselben
        # Tabelle → die Frage "landet breit" in der Tabelle (z.B. "Welche Wellen
        # gibt es?" trifft viele Zeilen ähnlich stark). Nur für kleine Tabellen,
        # damit Einzelfakt-Fragen auf großen Tabellen den Kontext nicht fluten.
        if self.auto_table_context_rows <= 0:
            return None
        top_slice = hits[: self.top_k]
        table_hits = [h for h in top_slice if _is_table_hit(h)]
        if not table_hits:
            return None
        doc_hash, count = Counter(h.chunk.doc_hash for h in table_hits).most_common(1)[0]
        if 2 * count <= len(top_slice):  # keine Mehrheit
            return None
        # +1 als Größensentinel: kommen mehr Zeilen zurück als erlaubt, ist die
        # Tabelle zu groß für das automatische Voll-Laden ohne Listen-Signal.
        rows = scroll(doc_hash, limit=self.auto_table_context_rows + 1)
        if not rows or len(rows) > self.auto_table_context_rows:
            return None
        seed = next(h for h in table_hits if h.chunk.doc_hash == doc_hash)
        return self._as_table_context(rows, seed, route="table_dominance")

    def _as_table_context(self, rows: list[SearchResult], seed: SearchResult, *, route: str) -> tuple[list[RetrievedChunk], str]:
        """Alle Zeilen erben den Score des Seed-Treffers – für die Quellenanzeige
        zählt die Relevanz des Dokuments, nicht die der Einzelzeile."""
        logger.info(
            "table_context_routing route=%s doc_hash=%s rows=%d seed_score=%.3f",
            route, seed.chunk.doc_hash, len(rows), seed.score,
        )
        chunks = [
            RetrievedChunk(chunk=r.chunk, metadata=r.metadata, similarity=seed.score)
            for r in rows
        ]
        return chunks, route

    # ------------------------------------------------------------------
    # Nachvollziehbarkeit: Detailtext für den Prozess-Schritt "Chunk-Suche"
    # ------------------------------------------------------------------

    def _search_detail(self, chunks: list[RetrievedChunk], route: Optional[str]) -> str:
        """
        Menschlich lesbare Zusammenfassung des Suchergebnisses: welche Dateien
        (mit Seiten bzw. Tabellenzeilen und bestem Score), welche Route.
        Wird im GUI unter "Chunk-Suche" angezeigt.
        """
        if route is not None and chunks:
            label = "Signalwort erkannt" if route == "keyword" else "Treffer-Mehrheit in Tabelle"
            return (
                f"Tabellen-Route ({label}): „{_chunk_file_name(chunks[0])}“ vollständig geladen "
                f"– {len(chunks)} Zeilen (Relevanz {chunks[0].similarity * 100:.0f} %)."
            )

        if not chunks:
            return (
                f"Keine Treffer über den Schwellenwerten (Text ≥ {self.min_similarity:g}, "
                f"Tabellen ≥ {self.table_min_similarity:g})."
            )

        # Normaler top_k-Pfad: Treffer nach Datei gruppieren.
        by_file: dict[str, list[RetrievedChunk]] = {}
        for c in chunks:
            by_file.setdefault(_chunk_file_name(c), []).append(c)

        parts = []
        for name, group in by_file.items():
            is_table = group[0].metadata.get("doc_kind") == "table"
            if is_table:
                lines = ", ".join(str(c.chunk.position) for c in group[:4])
                where = f"Zeile(n) {lines}"
            else:
                pages = sorted({c.chunk.page_number for c in group})
                where = "S. " + ", ".join(str(p) for p in pages[:4])
            best = max(c.similarity for c in group)
            parts.append(f"„{name}“ ({where}, max. {best * 100:.0f} %)")

        return f"{len(chunks)} Treffer: " + "; ".join(parts)


def _chunk_file_name(c: RetrievedChunk) -> str:
    """Sichtbarer Dateiname eines Chunks: Dokumenttitel, sonst Dateiname des Upload-Pfads."""
    return str(c.metadata.get("file_name") or Path(c.chunk.source_path).name or "unbekannt")
