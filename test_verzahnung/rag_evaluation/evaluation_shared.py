"""Gemeinsame Hilfen für create_testset.py, evaluation_llm.ipynb und evaluation_final.ipynb.

Aufgabenteilung:
- create_testset.py erzeugt EINMALIG das Frage-Chunk-Testset (inkl. Chunk-Embedding).
- Beide Evaluationsnotebooks LADEN nur dieses Testset und durchlaufen damit die Pipeline.
"""

from __future__ import annotations

import datetime
import inspect
import json
import math
import random
import re
import time
from pathlib import Path
from typing import Any


# Schema 2: jedes Item enthält zusätzlich den Embedding-Vektor seines Chunks.
TESTSET_SCHEMA_VERSION = 2


def kosinus_aehnlichkeit(a, b) -> float:
    """Kosinus-Ähnlichkeit zweier Vektoren."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


def lade_alle_qdrant_chunks(store, collection_name: str, *, batch_size: int = 256) -> list[dict[str, Any]]:
    """Liest alle texttragenden Punkte der Collection paginiert aus."""
    if not hasattr(store, "client"):
        raise TypeError(f"{type(store).__name__} stellt keinen Qdrant-Client bereit.")

    chunks: list[dict[str, Any]] = []
    offset = None
    while True:
        punkte, offset = store.client.scroll(
            collection_name=collection_name,
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for punkt in punkte:
            payload = dict(punkt.payload or {})
            text = str(payload.get("text") or "").strip()
            if not text:
                continue
            source_path = str(payload.get("source_path") or "")
            source_name = (
                str(payload.get("file_name") or "").strip()
                or Path(source_path).name
                or "Unbekannte Quelle"
            )
            chunks.append(
                {
                    "point_id": str(punkt.id),
                    "chunk_text": text,
                    "source_path": source_path,
                    "source_name": source_name,
                    "page_number": int(payload.get("page_number") or 0),
                    "doc_hash": str(payload.get("doc_hash") or ""),
                    "position": int(payload.get("position") or 0),
                }
            )
        if offset is None:
            break
    return chunks


def frage_prompt(chunk_text: str) -> str:
    """Prompt, der GENAU EINE auf den Chunk zielende Fachfrage erzeugt."""
    return (
        "Formuliere GENAU EINE fachliche Frage auf Deutsch, die sich AUSSCHLIESSLICH "
        "mit dem Inhalt des folgenden Textabschnitts beantworten lässt. Die Frage muss "
        "spezifisch auf genannte Fakten, Begriffe oder Werte abzielen, darf den Abschnitt "
        "aber nicht zitieren. Gib NUR die Frage aus, ohne Vor- oder Nachtext.\n\n"
        f"ABSCHNITT:\n{chunk_text[:3500]}"
    )


def saeubere_frage(text: str) -> str:
    """Reduziert die LLM-Ausgabe auf eine einzelne, saubere Frage."""
    zeilen = [zeile.strip() for zeile in str(text or "").splitlines() if zeile.strip()]
    if not zeilen:
        return ""
    frage = re.sub(
        r"^(frage\s*:\s*|[-*•]\s*|\d+[.)]\s*)",
        "",
        zeilen[0],
        flags=re.IGNORECASE,
    ).strip().strip('"').strip()
    if not frage:
        return ""
    if "?" in frage:
        return frage[: frage.find("?") + 1]
    return frage + "?"


def erstelle_testset(
    *,
    store,
    embedder,
    collection_name: str,
    frage_client,
    model_name: str,
    n_items: int,
    random_seed: int,
) -> dict[str, Any]:
    """
    Erzeugt das Frage-Chunk-Testset aus der gesamten Wissensbasis.

    1. Liest ALLE texttragenden Qdrant-Punkte der Collection.
    2. Zieht reproduzierbar (random_seed) n_items zufällige Chunks.
    3. Erzeugt pro Chunk via `model_name` eine spezifische Frage.
    4. Bettet jeden Chunk ein und legt den Vektor mit ab.
    """
    alle_chunks = lade_alle_qdrant_chunks(store, collection_name)
    if not alle_chunks:
        raise RuntimeError(
            f"Collection '{collection_name}' enthält keine Chunks. "
            "Bitte zuerst die Wissensbasis indexieren."
        )

    anzahl = min(int(n_items), len(alle_chunks))
    rng = random.Random(random_seed)
    kandidaten = rng.sample(alle_chunks, k=anzahl)

    # Embeddings der ausgewählten Chunks gebündelt berechnen (ein Vektorraum, L2-normalisiert).
    chunk_vektoren = embedder.embed([chunk["chunk_text"] for chunk in kandidaten]).dense_vectors

    items: list[dict[str, Any]] = []
    for index, (chunk, vektor) in enumerate(zip(kandidaten, chunk_vektoren), start=1):
        print(f"[Testset {index}/{anzahl}] Erzeuge Frage ...", end=" ", flush=True)
        try:
            rohtext = frage_client.generate(
                model=model_name,
                prompt=frage_prompt(chunk["chunk_text"]),
                temperature=0.0,
                max_tokens=72,
            )
            frage = saeubere_frage(rohtext)
        except Exception as exc:
            raise RuntimeError(
                f"Fragegenerierung für Testfall {index} fehlgeschlagen: {exc}"
            ) from exc
        if len(frage) < 10:
            raise RuntimeError(f"Testfall {index} lieferte keine gültige Frage.")

        items.append(
            {
                "id": f"rag_eval_{index:03d}",
                "question": frage,
                "embedding": vektor,
                **chunk,
            }
        )
        print(frage)

    return {
        "schema_version": TESTSET_SCHEMA_VERSION,
        "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "collection_name": collection_name,
        "generator_model": model_name,
        "embedding_dim": len(chunk_vektoren[0]) if chunk_vektoren else 0,
        "random_seed": random_seed,
        "qdrant_chunks_total": len(alle_chunks),
        "selection": "random.sample über alle texttragenden Punkte der Collection",
        "n_items": len(items),
        "items": items,
    }


def speichere_testset(daten: dict[str, Any], testset_path: Path) -> None:
    """Schreibt das Testset atomar (über eine temporäre Datei)."""
    testset_path = Path(testset_path)
    testset_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = testset_path.with_suffix(testset_path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(daten, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(testset_path)


def lade_testset(testset_path: Path) -> dict[str, Any]:
    """Lädt und validiert ein zuvor erstelltes Testset."""
    testset_path = Path(testset_path)
    if not testset_path.exists():
        raise FileNotFoundError(
            f"Testset {testset_path} fehlt. Bitte zuerst create_testset.py ausführen."
        )
    daten = json.loads(testset_path.read_text(encoding="utf-8"))
    if daten.get("schema_version") != TESTSET_SCHEMA_VERSION:
        raise ValueError(
            f"Testset {testset_path} hat Schema-Version {daten.get('schema_version')}, "
            f"erwartet wird {TESTSET_SCHEMA_VERSION}. Bitte mit create_testset.py neu erzeugen."
        )
    items = daten.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError(f"Testset {testset_path} enthält keine Fälle.")
    for index, item in enumerate(items, start=1):
        if not str(item.get("question") or "").strip():
            raise ValueError(f"Testset {testset_path}: Frage in Fall {index} fehlt.")
        if not str(item.get("chunk_text") or "").strip():
            raise ValueError(f"Testset {testset_path}: Chunk in Fall {index} fehlt.")
        if not isinstance(item.get("embedding"), list) or not item["embedding"]:
            raise ValueError(f"Testset {testset_path}: Embedding in Fall {index} fehlt.")
    return daten


def rufe_retriever_auf(retriever, frage: str, cad_metadata: dict[str, Any]):
    """Unterstützt aktuelle und ältere Retriever-Signaturen."""
    parameter = inspect.signature(retriever.retrieve).parameters
    if "cad_metadata" in parameter:
        return retriever.retrieve(frage, cad_metadata=cad_metadata)
    return retriever.retrieve(frage)


def generiere_antwort(
    answer_generator,
    *,
    frage: str,
    treffer,
    cad_metadata: dict[str, Any],
    output_format: str,
):
    """Unterstützt aktuelle und ältere Antwortgenerator-Signaturen."""
    parameter = inspect.signature(answer_generator.generate).parameters
    kwargs = {
        "question": frage,
        "chunks": treffer,
        "cad_metadata": cad_metadata,
    }
    if "output_format" in parameter:
        kwargs["output_format"] = output_format
    else:
        kwargs["answer_format"] = output_format
    return answer_generator.generate(**kwargs)


def restbudget_ok(startzeit: float, max_runtime_seconds: int, reserve_seconds: int = 75) -> bool:
    """True, wenn vor dem nächsten LLM-Fall noch ausreichend Laufzeitbudget besteht."""
    return (time.monotonic() - startzeit) <= (max_runtime_seconds - reserve_seconds)


def kuerzen(text: Any, laenge: int = 180) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text if len(text) <= laenge else text[: laenge - 1] + "…"
