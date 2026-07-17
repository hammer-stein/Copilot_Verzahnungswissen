"""
qdrant_store.py – Vektordatenbank-Adapter für Qdrant.

Implementiert das VectorStore-Protokoll. Speichert Chunks als Qdrant-Punkte mit
Vektor + Payload (Text, doc_hash, Sparse-Vektor) und führt die Vektorsuche aus.
Punkt-IDs sind deterministisch aus (doc_hash, position) gehasht.
"""

from __future__ import annotations

import hashlib
from typing import Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from app.core.types import DocumentInfo, EmbeddedChunk, SearchResult


class QdrantStore:
    """Adapter zwischen dem RAG-System und der Qdrant-Vektordatenbank."""

    def __init__(self, *, host: str, port: int, collection_name: str, path: Optional[str] = None) -> None:
        """
        Verbindet sich mit Qdrant. Ist `path` gesetzt, läuft Qdrant eingebettet (lokaler
        On-Disk-Modus, kein Server/Docker nötig); andernfalls per HTTP über host/port.
        Die Collection wird lazy beim ersten upsert() angelegt.
        """
        if path:
            self.client = QdrantClient(path=path)  # eingebetteter On-Disk-Modus
        else:
            self.client = QdrantClient(host=host, port=port)
        self.collection_name = collection_name

    def _collection_exists(self) -> bool:
        """
        True, wenn die Collection bereits angelegt wurde. Sie entsteht erst beim ersten upsert(),
        daher müssen Lese-Operationen (search, list_documents) eine fehlende Collection tolerieren
        und eine leere Wissensbasis als leeres Ergebnis behandeln statt zu scheitern.
        """
        try:
            return self.client.collection_exists(self.collection_name)
        except Exception:
            try:
                return any(c.name == self.collection_name for c in self.client.get_collections().collections)
            except Exception:
                return False

    def _ensure_collection(self, vector_size: int) -> None:
        """
        Legt die Collection mit COSINE-Distanzmetrik an, falls sie noch nicht existiert.
        Erstellt zusätzlich Payload-Indizes für doc_hash und source_path zur Beschleunigung von Filterabfragen.
        """
        collections = self.client.get_collections().collections
        if any(c.name == self.collection_name for c in collections):
            return  # bereits vorhanden

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        # KEYWORD-Index für exakte String-Filterabfragen (O(log n) statt linearer Scan)
        self.client.create_payload_index(
            collection_name=self.collection_name, field_name="doc_hash", field_schema=PayloadSchemaType.KEYWORD,
        )
        self.client.create_payload_index(
            collection_name=self.collection_name, field_name="source_path", field_schema=PayloadSchemaType.KEYWORD,
        )

    def upsert(self, chunks: list[EmbeddedChunk]) -> None:
        """
        Speichert EmbeddedChunks als Qdrant-Punkte (Insert or Update).
        Derselbe Chunk bekommt immer dieselbe ID (Hash aus doc_hash + position),
        sodass erneutes Hochladen überschreibt statt Duplikate zu erzeugen.
        """
        if not chunks:
            return

        self._ensure_collection(vector_size=len(chunks[0].dense_vector))

        points: list[PointStruct] = []
        for ec in chunks:
            c = ec.chunk
            meta = ec.metadata or {}
            payload: dict[str, Any] = {
                "text": c.text,
                "source_path": c.source_path,
                "page_number": c.page_number,
                "position": c.position,
                "doc_hash": c.doc_hash,
                "metadata": meta,
                "sparse_vector": ec.sparse_vector or {},
                # Dokument-Ebene: aus der Metadaten-Bag auf Top-Level gehoben, damit
                # list_documents und set_document_folder sie ohne JSON-Parsing lesen/schreiben können.
                "file_name": str(meta.get("file_name", "")),
                "folder": str(meta.get("folder", "")),
                "doc_kind": str(meta.get("doc_kind", "text")),  # "text" | "table" – für Aggregat-Routing
            }
            # Stabiler Integer-ID über Prozesse hinweg.
            digest = hashlib.sha256(f"{c.doc_hash}:{c.position}".encode("utf-8")).digest()
            pid = int.from_bytes(digest[:8], "big") % (2**63)
            points.append(PointStruct(id=pid, vector=ec.dense_vector, payload=payload))

        self.client.upsert(collection_name=self.collection_name, points=points)

    def search(
        self,
        query_vector: list[float],
        *,
        top_k: int,
        threshold: float,
        query_sparse_vector: Optional[dict[str, float]] = None,
        use_hybrid: bool = False,
        hybrid_dense_weight: float = 0.7,
        hybrid_sparse_weight: float = 0.3,
    ) -> list[SearchResult]:
        """
        Führt die Vektorsuche aus. query_points() ist die aktuelle API
        (Qdrant >= 1.10, ersetzt das veraltete search()).
        Hybrid-Search nutzt Qdrant für dichte Kandidaten und rerankt diese lokal mit Sparse-Scores.
        """
        if not self._collection_exists():
            return []  # leere Wissensbasis (noch nichts indexiert)
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=top_k,
            score_threshold=threshold,
            with_payload=True,
        )

        out: list[SearchResult] = []
        for h in response.points:  # response.points: Liste von ScoredPoint
            p = h.payload or {}
            dense_score = float(h.score) if h.score is not None else 0.0
            sparse_score = None
            final_score = dense_score
            if use_hybrid and query_sparse_vector:
                sparse_score = _sparse_dot(query_sparse_vector, p.get("sparse_vector") or {})
                final_score = (
                    float(hybrid_dense_weight) * dense_score
                    + float(hybrid_sparse_weight) * sparse_score
                )
            out.append(
                SearchResult(
                    chunk=_payload_to_chunk(p),
                    metadata=_payload_to_metadata(p),
                    dense_score=dense_score,
                    sparse_score=sparse_score,
                    score=final_score,
                )
            )
        return sorted(out, key=lambda r: r.score, reverse=True)

    def scroll_by_doc_hash(self, doc_hash: str, *, limit: int) -> list[SearchResult]:
        """
        Lädt alle Chunks eines Dokuments (ohne Vektorsuche), sortiert nach position –
        bei Tabellen-Dokumenten entspricht das der ursprünglichen Zeilenreihenfolge.
        Grundlage für das Aggregat-Routing des Retrievers ("zeige alle …"), das bei
        Listenfragen die ganze Tabelle statt nur top_k Treffer als Kontext lädt.
        """
        if not self._collection_exists():
            return []

        results: list[SearchResult] = []
        offset = None  # Scroll-Cursor, None = Anfang
        while len(results) < limit:
            points, offset = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[FieldCondition(key="doc_hash", match=MatchValue(value=doc_hash))]
                ),
                limit=min(256, limit - len(results)),
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for pt in points:
                p = pt.payload or {}
                results.append(
                    SearchResult(
                        chunk=_payload_to_chunk(p),
                        metadata=_payload_to_metadata(p),
                        dense_score=None,
                        sparse_score=None,
                        score=0.0,  # kein Suchscore – der Retriever übernimmt den Score des Seed-Treffers
                    )
                )
            if offset is None:  # keine weiteren Seiten
                break

        return sorted(results, key=lambda r: r.chunk.position)[:limit]

    def delete_by_doc_hash(self, doc_hash: str) -> None:
        """Löscht alle Chunks eines Dokuments anhand des doc_hash (Mechanismus für DELETE /documents/{doc_hash})."""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[FieldCondition(key="doc_hash", match=MatchValue(value=doc_hash))]
            ),
        )

    def clear_all(self) -> None:
        """
        Leert die komplette Wissensbasis: Die gesamte Collection wird gelöscht
        (Mechanismus für DELETE /documents – "Alle löschen"). Sie wird beim nächsten
        upsert() lazy neu angelegt, sodass eine geleerte Wissensbasis genauso
        konsistent leer ist wie eine frisch installierte (keine verwaisten Punkte).
        """
        if self._collection_exists():
            self.client.delete_collection(collection_name=self.collection_name)

    def set_document_folder(self, doc_hash: str, folder: str) -> None:
        """
        Ordnet ein Dokument einem Ordner zu, indem das Payload-Feld "folder" für ALLE
        Chunks dieses doc_hash gesetzt wird. set_payload aktualisiert nur die genannten
        Felder; Text, Vektor und übrige Payload bleiben unangetastet.
        """
        if not self._collection_exists():
            return
        self.client.set_payload(
            collection_name=self.collection_name,
            payload={"folder": str(folder or "")},
            points=Filter(
                must=[FieldCondition(key="doc_hash", match=MatchValue(value=doc_hash))]
            ),
        )

    def set_document_title(self, doc_hash: str, title: str) -> None:
        """
        Speichert den Anzeigenamen eines Dokuments an allen Chunks. Die Quellenausgabe
        nutzt später genau dieses Payload-Feld statt des anonymisierten Upload-Pfads.
        """
        if not self._collection_exists():
            return
        self.client.set_payload(
            collection_name=self.collection_name,
            payload={"file_name": str(title or "")},
            points=Filter(
                must=[FieldCondition(key="doc_hash", match=MatchValue(value=doc_hash))]
            ),
        )

    def list_documents(self) -> list[DocumentInfo]:
        """
        Gibt alle indizierten Dokumente mit Chunk-Anzahl zurück.
        Qdrant hat kein natives GROUP BY – alle Punkte werden per scroll() seitenweise
        durchlaufen und nach doc_hash aggregiert.
        """
        if not self._collection_exists():
            return []  # noch nichts indexiert → leere Wissensbasis

        docs: dict[str, DocumentInfo] = {}
        offset = None  # Scroll-Cursor, None = Anfang

        while True:
            points, offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=256,
                offset=offset,
                with_payload=["source_path", "doc_hash", "file_name", "folder"],
                with_vectors=False,
            )
            for pt in points:
                payload = pt.payload or {}
                dh = str(payload.get("doc_hash", ""))
                sp = str(payload.get("source_path", ""))
                fn = str(payload.get("file_name", "") or "")
                fld = str(payload.get("folder", "") or "")
                if not dh:
                    continue
                if dh not in docs:
                    docs[dh] = DocumentInfo(source_path=sp, doc_hash=dh, chunk_count=1, file_name=fn, folder=fld)
                else:
                    prev = docs[dh]
                    docs[dh] = DocumentInfo(
                        source_path=prev.source_path or sp,
                        doc_hash=dh,
                        chunk_count=prev.chunk_count + 1,
                        file_name=prev.file_name or fn,
                        folder=prev.folder or fld,
                    )

            if offset is None:  # keine weiteren Seiten
                break

        return sorted(docs.values(), key=lambda d: (d.folder.casefold(), (d.file_name or d.source_path).casefold()))


def _payload_to_chunk(payload: dict[str, Any]):
    """Rekonstruiert ein Chunk-Objekt aus dem Qdrant-Payload. Fehlende Felder werden durch Standardwerte ersetzt."""
    from app.core.types import Chunk
    return Chunk(
        text=str(payload.get("text", "")),
        source_path=str(payload.get("source_path", "")),
        page_number=int(payload.get("page_number", 0) or 0),
        position=int(payload.get("position", 0) or 0),
        doc_hash=str(payload.get("doc_hash", "")),
    )


def _payload_to_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Kombiniert die freie Chunk-Metadaten-Bag mit Dokument-Metadaten auf Top-Level.
    Ältere Punkte enthalten file_name teilweise nur auf Top-Level; der AnswerGenerator
    braucht diese Information für sprechende Quellen statt technischer Upload-Pfade.
    """
    metadata = dict(payload.get("metadata") or {})
    for key in ("file_name", "folder", "doc_hash", "source_path", "doc_kind"):
        value = payload.get(key)
        if value not in (None, "") and not metadata.get(key):
            metadata[key] = value
    return metadata


def _sparse_dot(a: dict[str, float], b: dict[str, Any]) -> float:
    """Skalarprodukt zweier bereits normalisierter lexikalischer Sparse-Vektoren."""
    if not a or not b:
        return 0.0
    if len(a) > len(b):
        a, b = b, a
    score = 0.0
    for key, val in a.items():
        try:
            score += float(val) * float(b.get(key, 0.0))
        except Exception:
            continue
    return score
