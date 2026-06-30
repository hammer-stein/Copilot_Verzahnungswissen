"""
create_testset.py – Erzeugt EINMALIG das gemeinsame RAG-Evaluations-Testset.

Ablauf:
  1. Wählt N zufällige Chunks aus der gesamten, im Hauptmodell hochgeladenen
     Wissensbasis (Qdrant-Collection aus config.yaml).
  2. Erzeugt zu jedem Chunk via wählbarem LLM (Standard: llama3.2:3b) eine
     spezifische Frage, die genau auf den Chunk-Inhalt abzielt.
  3. Bettet jeden Chunk ein und speichert Frage + Chunk + Embedding-Vektor.

Das Ergebnis (rag_evaluation_testset.json) ist die gemeinsame Grundlage für
evaluation_llm.ipynb und evaluation_final.ipynb. Dieses Skript muss nur einmal
laufen; eine vorhandene Datei wird nur mit FORCE_NEU=True überschrieben.

Aufruf (aus dem Projekt-Root):
    python -m test_verzahnung.rag_evaluation.create_testset
    python test_verzahnung/rag_evaluation/create_testset.py
"""

from __future__ import annotations

import sys
from pathlib import Path


# ============================================================
# KONFIGURATION – hier Generator-LLM und Umfang wählen
# ============================================================
N_ITEMS = 20                     # Anzahl zufälliger Chunks / Testfälle
RANDOM_SEED = 42                 # reproduzierbare Zufallsauswahl
GENERATOR_MODEL = "llama3.2:3b"  # LLM für die Fragengenerierung (z. B. "llama3.1:8b")
FORCE_NEU = True                # True überschreibt ein vorhandenes Testset bewusst


def main() -> None:
    hier = Path(__file__).resolve()
    project_root = next(
        (
            pfad
            for pfad in (hier.parent, *hier.parents)
            if (pfad / "config.yaml").exists() and (pfad / "app").exists()
        ),
        None,
    )
    if project_root is None:
        raise FileNotFoundError("Projekt-Root (mit config.yaml und app/) nicht gefunden.")
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from app.core.config import load_config
    from app.core.factory import build_components
    from app.implementations.ollama_client import OllamaClient
    from test_verzahnung.rag_evaluation.evaluation_shared import erstelle_testset, speichere_testset

    testset_path = hier.parent / "rag_evaluation_testset.json"
    if testset_path.exists() and not FORCE_NEU:
        print(f"Testset existiert bereits: {testset_path}")
        print("Es wird nichts überschrieben. Für ein bewusst neues Set: FORCE_NEU = True setzen.")
        return

    config = load_config(project_root / "config.yaml")
    collection_name = config.vector_store.collection_name

    # Die Testset-Erzeugung nutzt nur Embedder und Vektorspeicher. Der CAD-Adapter
    # ist irrelevant und wird auf synthetic_json gestellt, damit kein OCC/STEP nötig ist.
    config = config.model_copy(
        update={
            "cad_adapter": config.cad_adapter.model_copy(
                update={"implementation": "synthetic_json"}
            )
        }
    )

    print("Baue Embedder und Vektorspeicher aus der Konfiguration auf ...")
    components = build_components(config, base_dir=project_root)

    frage_client = OllamaClient(
        base_url=config.answer_generator.ollama_url,
        timeout_s=60,
    )

    print("\nTestset-Erzeugung")
    print(f"  Collection:       {collection_name}")
    print(f"  Generator-Modell: {GENERATOR_MODEL}")
    print(f"  Anzahl Fälle:     {N_ITEMS}")
    print(f"  Random-Seed:      {RANDOM_SEED}\n")

    daten = erstelle_testset(
        store=components.vector_store,
        embedder=components.embedder,
        collection_name=collection_name,
        frage_client=frage_client,
        model_name=GENERATOR_MODEL,
        n_items=N_ITEMS,
        random_seed=RANDOM_SEED,
    )
    speichere_testset(daten, testset_path)

    print(f"\nFertig: {daten['n_items']} Fälle gespeichert in {testset_path}")
    print(f"Zufallsbasis: {daten['qdrant_chunks_total']} Chunks, Embedding-Dimension {daten['embedding_dim']}.")


if __name__ == "__main__":
    main()
