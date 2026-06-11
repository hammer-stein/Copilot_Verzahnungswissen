"""
qdrant_store.py – Vektordatenbank-Adapter für Qdrant.

Implementiert das VectorStore-Protokoll. Speichert Chunks als Qdrant-Punkte mit
Vektor + Payload (Text, Metadaten, doc_hash) und ermöglicht kombinierte Vektor-
und Metadaten-Filtersuche. Punkt-IDs sind deterministisch aus (doc_hash, position) gehasht.
"""

from __future__ import annotations

import hashlib
from typing import Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    IsEmptyCondition,
    MatchValue,
    PayloadField,
    PayloadSchemaType,
    PointStruct,
    Range,
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
        for field_name, field_schema in [
            ("metadata.verzahnungstyp", PayloadSchemaType.KEYWORD),
            ("metadata.modul_min", PayloadSchemaType.FLOAT),
            ("metadata.modul_max", PayloadSchemaType.FLOAT),
        ]:
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field_name,
                    field_schema=field_schema,
                )
            except Exception:
                pass

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
            payload: dict[str, Any] = {
                "text": c.text,
                "source_path": c.source_path,
                "page_number": c.page_number,
                "position": c.position,
                "doc_hash": c.doc_hash,
                "metadata": ec.metadata or {},
                "sparse_vector": ec.sparse_vector or {},
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
        filter: dict,
        top_k: int,
        threshold: float,
        query_sparse_vector: Optional[dict[str, float]] = None,
        use_hybrid: bool = False,
        hybrid_dense_weight: float = 0.7,
        hybrid_sparse_weight: float = 0.3,
    ) -> list[SearchResult]:
        """
        Führt eine kombinierte Vektor- und Metadaten-Filtersuche aus.
        query_points() ist die aktuelle API (Qdrant >= 1.10, ersetzt das veraltete search()).
        Hybrid-Search nutzt Qdrant für dichte Kandidaten und rerankt diese lokal mit Sparse-Scores.
        """
        if not self._collection_exists():
            return []  # leere Wissensbasis (noch nichts indexiert)

        qfilter = _dict_filter_to_qdrant(filter)

        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=qfilter,      # None = kein Filter
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
                    metadata=(p.get("metadata") or {}),
                    dense_score=dense_score,
                    sparse_score=sparse_score,
                    score=final_score,
                )
            )
        return sorted(out, key=lambda r: r.score, reverse=True)

    def delete_by_doc_hash(self, doc_hash: str) -> None:
        """Löscht alle Chunks eines Dokuments anhand des doc_hash (Mechanismus für DELETE /documents/{doc_hash})."""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
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
                with_payload=["source_path", "doc_hash"],
                with_vectors=False,
            )
            for pt in points:
                payload = pt.payload or {}
                dh = str(payload.get("doc_hash", ""))
                sp = str(payload.get("source_path", ""))
                if not dh:
                    continue
                if dh not in docs:
                    docs[dh] = DocumentInfo(source_path=sp, doc_hash=dh, chunk_count=1)
                else:
                    prev = docs[dh]
                    docs[dh] = DocumentInfo(source_path=prev.source_path or sp, doc_hash=dh, chunk_count=prev.chunk_count + 1)

            if offset is None:  # keine weiteren Seiten
                break

        return sorted(docs.values(), key=lambda d: d.source_path)


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


def _dict_filter_to_qdrant(filter_dict: dict) -> Optional[Filter]:
    """
    Wandelt das interne Filter-Dict in Qdrant-Filter-Objekte um.
    or_empty=True kombiniert jede Bedingung mit IsEmpty (OR) – Chunks ohne das Feld werden nicht ausgeschlossen.
    """
    if not filter_dict:
        return None

    must_conditions = []
    for cond in filter_dict.get("must", []):
        key = cond["key"]
        or_empty = bool(cond.get("or_empty", False))

        if "match" in cond:
            c = FieldCondition(key=key, match=MatchValue(value=cond["match"]))
        elif "contains" in cond:
            c = FieldCondition(key=key, match=MatchValue(value=cond["contains"]))
        elif "range" in cond:
            r = cond["range"]
            c = FieldCondition(key=key, range=Range(gte=r.get("gte"), lte=r.get("lte")))
        else:
            continue  # unbekannter Typ

        if or_empty:
            # OR-Verknüpfung: Bedingung ODER Feld fehlt (Großzügigkeitsprinzip)
            must_conditions.append(
                Filter(should=[c, IsEmptyCondition(is_empty=PayloadField(key=key))])
            )
        else:
            must_conditions.append(c)

    return Filter(must=must_conditions or None)


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
