"""
chunker_recursive.py – Regelbasierter Chunker nach Token-Limit.

Implementiert das Chunker-Protokoll als schnelle Alternative zum SemanticChunker.
Sätze werden sequentiell zusammengefügt bis das Token-Limit erreicht ist –
ohne Embedding-Aufrufe, deterministisch und ressourcenschonend.

Tabellen-Dokumente (RawDocument.doc_kind == "table", z.B. aus dem TabularLoader)
werden zeilenweise gechunkt: jede Zeile ist ein atomarer Datensatz und darf
weder mit Nachbarzeilen verschmolzen noch am Token-Limit zerschnitten werden.
"""

from __future__ import annotations

from app.core.types import Chunk, RawDocument
from app.implementations.text_split import approx_tokens, chunk_table_rows, split_sentences


class RecursiveTextChunker:
    """Teilt Dokumente regelbasiert nach Token-Limit in Chunks auf – kein Embedding-Aufruf nötig."""

    def __init__(
        self,
        *,
        min_chunk_tokens: int,
        max_chunk_tokens: int,
        overlap_sentences: int,
    ) -> None:
        """
        min_chunk_tokens verhindert winzige Chunks aus leeren Seiten.
        overlap_sentences sorgt für Kontextkontinuität an Chunk-Grenzen.
        """
        self.min_chunk_tokens = min_chunk_tokens
        self.max_chunk_tokens = max_chunk_tokens
        self.overlap_sentences = max(0, overlap_sentences)

    def chunk(self, document: RawDocument) -> list[Chunk]:
        """
        Verarbeitet jede Seite seitenweise: Sätze sammeln bis Token-Limit →
        Chunk speichern → mit Overlap weitermachen.
        position ist dokumentweit monoton steigend.
        """
        if document.doc_kind == "table":
            return chunk_table_rows(document)

        chunks: list[Chunk] = []
        pos = 0

        for page in document.pages:
            sentences = split_sentences(page.text)
            if not sentences:
                continue

            start = 0
            while start < len(sentences):
                cur, cur_tokens, i = [], 0, start

                while i < len(sentences):
                    s_tokens = approx_tokens(sentences[i])
                    # ersten Satz immer hinzufügen (auch wenn er allein das Limit überschreitet)
                    if cur and (cur_tokens + s_tokens) > self.max_chunk_tokens:
                        break
                    cur.append(sentences[i])
                    cur_tokens += s_tokens
                    i += 1

                text = " ".join(cur).strip()
                if text and cur_tokens >= self.min_chunk_tokens:
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

                # Schutz vor Endlosschleife wenn ein Satz länger als max_chunk_tokens ist
                if i <= start:
                    start += 1
                else:
                    start = max(i - self.overlap_sentences, start + 1)

        return chunks
