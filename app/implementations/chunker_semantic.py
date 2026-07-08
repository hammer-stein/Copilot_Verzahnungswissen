"""
chunker_semantic.py – Semantischer Chunker basierend auf Embedding-Ähnlichkeit.

Implementiert das Chunker-Protokoll. Setzt Chunk-Grenzen dort, wo die Kosinus-Ähnlichkeit
zwischen benachbarten Sätzen unter einen Schwellenwert fällt – so entstehen thematisch
kohärente Segmente statt willkürlicher Token-Schnitte.
"""

from __future__ import annotations

import math

from app.core.interfaces import Embedder
from app.core.types import Chunk, RawDocument
from app.implementations.text_split import approx_tokens, chunk_table_rows, split_sentences


def _cosine(a: list[float], b: list[float]) -> float:
    """
    Berechnet die Kosinus-Ähnlichkeit zweier Vektoren.
    Da der Embedder L2-normalisiert, ist das Ergebnis gleich dem Skalarprodukt –
    die explizite Normalisierung hier macht die Funktion robust für Tests.
    """
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0  # or 1.0 verhindert Division durch 0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


class SemanticChunker:
    """Teilt Dokumente anhand semantischer Ähnlichkeit in thematisch kohärente Chunks auf."""

    def __init__(
        self,
        *,
        embedder: Embedder,
        threshold: float,
        min_chunk_tokens: int,
        max_chunk_tokens: int,
        overlap_sentences: int,
    ) -> None:
        """
        threshold bestimmt die Grenzempfindlichkeit: niedrig = viele kleine Chunks, hoch = wenige große.
        overlap_sentences verhindert Informationsverlust exakt an Chunk-Grenzen.
        """
        self.embedder = embedder
        self.threshold = threshold
        self.min_chunk_tokens = min_chunk_tokens
        self.max_chunk_tokens = max_chunk_tokens
        self.overlap_sentences = max(0, overlap_sentences)

    def chunk(self, document: RawDocument) -> list[Chunk]:
        """
        Verarbeitet jede Seite seitenweise: Sätze einbetten → Grenzen finden →
        Segmente packen → Chunk-Objekte erzeugen.
        Position ist dokumentweit monoton steigend (nicht seitenweise).
        """
        if document.doc_kind == "table":
            # Tabellen zeilenweise chunken – semantisches Verschmelzen würde
            # Datensätze vermischen und kurze Zeilen am min_chunk_tokens-Filter verlieren.
            return chunk_table_rows(document)

        chunks: list[Chunk] = []
        pos = 0  # dokumentweiter Zähler für stabile Qdrant-Punkt-IDs

        for page in document.pages:
            sentences = split_sentences(page.text)
            if len(sentences) < 2:
                continue  # Seiten mit 0–1 Sätzen überspringen

            # Alle Sätze der Seite in einem Batch einbetten (effizienter als einzeln)
            sent_vecs = self.embedder.embed(sentences).dense_vectors

            # Grenzen setzen wo Ähnlichkeit unter threshold fällt
            boundaries: set[int] = set()
            for i in range(1, len(sentences)):
                if _cosine(sent_vecs[i - 1], sent_vecs[i]) < self.threshold:
                    boundaries.add(i)  # Grenze vor Satz i

            # Grenzen → Segmente (jedes Segment = zusammenhängende Satzgruppe)
            cuts = [0] + sorted(boundaries) + [len(sentences)]
            segments = [sentences[a:b] for a, b in zip(cuts, cuts[1:]) if sentences[a:b]]

            def pack_segment(seg: list[str]) -> list[list[str]]:
                """Packt ein Segment in mehrere Token-begrenzte Satzgruppen mit Overlap."""
                packed = []
                start = 0
                while start < len(seg):
                    cur, cur_tokens, i = [], 0, start
                    while i < len(seg):
                        t = approx_tokens(seg[i])
                        if cur and (cur_tokens + t) > self.max_chunk_tokens:
                            break
                        cur.append(seg[i])
                        cur_tokens += t
                        i += 1
                    packed.append(cur)
                    # Überlapp: nächster Chunk beginnt overlap_sentences Sätze vor Ende
                    start = max(i - self.overlap_sentences, start + 1)
                return packed

            for seg in segments:
                for sent_group in pack_segment(seg):
                    text = " ".join(sent_group).strip()
                    if not text or approx_tokens(text) < self.min_chunk_tokens:
                        continue  # zu kleine Chunks verwerfen
                    pos += 1
                    chunks.append(
                        Chunk(
                            text=text,
                            source_path=document.source_path,
                            page_number=page.page_number,
                            position=pos,
                            doc_hash=document.doc_hash,
                        )
                    )

        return chunks
