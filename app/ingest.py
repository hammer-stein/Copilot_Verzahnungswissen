"""
app/ingest.py – Einmaliges Bulk-Ingest der Wissensbasis (ohne Browser/HTTP).

Indexiert einen Ordner voller Dokumente (PDF/CSV/Excel) direkt über die Pipeline
(Loader → Chunker → Embedder → Qdrant). Das ist deutlich schneller und robuster als
der sequenzielle Einzel-Upload über die Web-GUI: kein HTTP-/FastAPI-Overhead pro
Datei, größere Embedding-Batches, unbeaufsichtigter Lauf mit Terminal-Fortschritt.

Der Datenbestand landet im selben Qdrant wie der Server (im Compose-Betrieb der
qdrant-Service) – die Dokumente sind damit sofort in der GUI sichtbar und bleiben
über Neustarts erhalten. Erneutes Ingest ist unbedenklich: Dokumente werden über
einen Inhalts-Hash geschlüsselt und überschrieben statt dupliziert.

Aufruf (Docker-Standardbetrieb; Dateien unter ./storage/<ordner> ablegen, da
./storage in den Container gemountet ist):

    # als eigener Einmal-Container (empfohlen – stört den laufenden Server nicht):
    docker compose run --rm app python -m app.ingest storage/ingest --folder "Normen"

    # Ordnerstruktur der Unterordner als Wissensbasis-Ordner übernehmen:
    docker compose run --rm app python -m app.ingest storage/ingest --preserve-folders

    # alternativ im bereits laufenden Container:
    docker compose exec app python -m app.ingest storage/ingest --folder "Normen"

Optionen:
    path                 Datei oder Ordner (rekursiv). Pfad im Container, z.B.
                         storage/ingest (= ./storage/ingest auf dem Host).
    --folder NAME        Ziel-Ordner in der Wissensbasis (Standard: keiner).
    --preserve-folders   Unterordnernamen als Wissensbasis-Ordner übernehmen.
    --batch-size N       Embedding-Batchgröße (Standard 32; größer = schneller, mehr RAM).
    --config PATH        Alternative config.yaml.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Iterator, Optional

from app.core.config import load_config
from app.core.factory import build_components
from app.core.folder_registry import FolderRegistry
from app.pipeline.indexer import KnowledgeBaseIndexer

# Dieselben Endungen wie der /upload-Endpunkt der Web-GUI.
ALLOWED_EXTENSIONS = (".pdf", ".csv", ".xlsx", ".xls")


def _file_sort_key(p: Path):
    """Kleinste Dateien zuerst: so wird der Großteil schnell indexiert und die
    wenigen sehr großen (langsam/speicherhungrig) kommen zuletzt — ein einzelner
    Riese blockiert dann nicht mehr den Rest."""
    try:
        size = p.stat().st_size
    except OSError:
        size = 0
    return (size, str(p))


def _iter_files(root: Path) -> Iterator[Path]:
    """Alle unterstützten Dateien unter root (rekursiv, KLEINSTE zuerst, ohne Punktdateien)."""
    if root.is_file():
        if root.suffix.lower() in ALLOWED_EXTENSIONS:
            yield root
        return
    candidates = [p for p in root.rglob("*")
                  if p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS and not p.name.startswith(".")]
    for path in sorted(candidates, key=_file_sort_key):
        yield path


def _target_folder(file_path: Path, root: Path, base_folder: str, preserve: bool) -> str:
    """
    Ziel-Ordner in der Wissensbasis: optionaler Basis-Ordner, ergänzt (bei
    --preserve-folders) um den Unterordnerpfad relativ zum Ingest-Wurzelordner.
    Beispiel: root=storage/ingest, file=.../Normen/DIN.pdf, base="" → "Normen".
    """
    parts: list[str] = []
    base = base_folder.strip().strip("/")
    if base:
        parts.append(base)
    if preserve and root.is_dir():
        rel = file_path.parent.relative_to(root)
        sub = str(rel).replace("\\", "/").strip("/")
        if sub and sub != ".":
            parts.append(sub)
    return "/".join(parts)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Bulk-Ingest der Wissensbasis (ohne Browser/HTTP).")
    parser.add_argument("path", help="Datei oder Ordner (rekursiv) mit PDF/CSV/Excel.")
    parser.add_argument("--folder", default="", help="Ziel-Ordner in der Wissensbasis (Standard: keiner).")
    parser.add_argument("--preserve-folders", action="store_true", help="Unterordner als Wissensbasis-Ordner übernehmen.")
    parser.add_argument("--batch-size", type=int, default=32, help="Embedding-Batchgröße (Standard 32; größer = schneller, mehr RAM).")
    parser.add_argument("--config", default=None, help="Pfad zur config.yaml (Standard: <repo>/config.yaml).")
    parser.add_argument(
        "--skip-existing", action=argparse.BooleanOptionalAction, default=True,
        help="Bereits indexierte Dateien (gleicher Dateiname + Ordner) überspringen "
             "→ macht den Lauf wiederaufnehmbar (Standard: an; --no-skip-existing zum Erzwingen).",
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Nach so vielen NEU verarbeiteten Dateien sauber beenden (0 = unbegrenzt). "
             "Für einen überwachten Batch-Lauf: jeder Aufruf startet einen frischen Container "
             "(begrenzter Speicher) und nimmt via --skip-existing wieder auf.",
    )
    args = parser.parse_args(argv)

    base_dir = Path(__file__).resolve().parents[1]
    config_path = Path(args.config) if args.config else (base_dir / "config.yaml")
    root = Path(args.path)
    if not root.is_absolute():
        root = base_dir / root

    if not root.exists():
        print(f"FEHLER: Pfad nicht gefunden: {root}", file=sys.stderr)
        return 2
    if not config_path.exists():
        print(f"FEHLER: config.yaml nicht gefunden: {config_path}", file=sys.stderr)
        return 2

    files = list(_iter_files(root))
    if not files:
        print(f"Keine unterstützten Dateien (PDF/CSV/Excel) unter {root} gefunden.", file=sys.stderr)
        return 1

    print(f"Lade Konfiguration … ({config_path})")
    config = load_config(config_path)
    if args.batch_size and args.batch_size > 0:
        config.embedder.batch_size = args.batch_size
    print(
        f"Baue Komponenten – der Embedder lädt einmalig (~10 s). "
        f"batch_size={config.embedder.batch_size}, device={config.embedder.device}"
    )
    components = build_components(config, base_dir=base_dir)
    indexer = KnowledgeBaseIndexer(
        loader=components.loader,
        chunker=components.chunker,
        embedder=components.embedder,
        store=components.vector_store,
    )
    folder_registry = FolderRegistry(base_dir / "storage" / "folders.json")

    # Wiederaufnahme: bereits indexierte (Dateiname, Ordner) einmalig ermitteln,
    # damit ein erneuter Lauf nach Abbruch nur die fehlenden Dateien verarbeitet.
    existing: set[tuple[str, str]] = set()
    if args.skip_existing:
        try:
            existing = {(d.file_name, d.folder) for d in indexer.list_documents()}
            print(f"Wiederaufnahme aktiv: {len(existing)} Dokument(e) bereits indexiert — werden übersprungen.")
        except Exception as exc:  # noqa: BLE001 - ohne Bestandsliste einfach alles verarbeiten
            print(f"Bestandsliste nicht lesbar ({exc}) — verarbeite alle Dateien.", file=sys.stderr)

    total = len(files)
    width = len(str(total))
    print(f"\nStarte Ingest: {total} Datei(en) aus {root}\n")

    ok = 0
    failed = 0
    skipped = 0
    chunks_total = 0
    started = time.monotonic()
    seen_folders: set[str] = set()

    for i, file_path in enumerate(files, start=1):
        target = _target_folder(file_path, root, args.folder, args.preserve_folders)
        prefix = f"[{i:>{width}}/{total}]"
        if args.skip_existing and (file_path.name, target) in existing:
            skipped += 1
            if target and target not in seen_folders:
                folder_registry.add(target)
                seen_folders.add(target)
            print(f"{prefix} ⏭ {file_path.name} (bereits indexiert)")
            continue
        try:
            info = indexer.index_document(file_path, file_name=file_path.name, folder=target)
            ok += 1
            chunk_count = int(getattr(info, "chunk_count", 0) or 0)
            chunks_total += chunk_count
            if target and target not in seen_folders:
                folder_registry.add(target)  # leere/neue Ordner sichtbar machen (wie /upload)
                seen_folders.add(target)
            elapsed = time.monotonic() - started
            rate = i / elapsed if elapsed > 0 else 0.0
            eta_min = ((total - i) / rate / 60) if rate > 0 else 0.0
            location = f" → {target}" if target else ""
            print(
                f"{prefix} ✓ {file_path.name}{location}  ({chunk_count} Chunks)  "
                f"[{i / total * 100:5.1f}% · {rate:.2f} Dateien/s · ETA {eta_min:.1f} min]"
            )
        except Exception as exc:  # noqa: BLE001 - eine kaputte Datei darf den Gesamtlauf nicht stoppen
            failed += 1
            print(f"{prefix} ✗ {file_path.name}  FEHLER: {type(exc).__name__}: {exc}", file=sys.stderr)

        if args.limit and (ok + failed) >= args.limit:
            print(f"--limit {args.limit} erreicht → sauberer Zwischenstopp (Rest via Wiederaufnahme).")
            break

    elapsed_min = (time.monotonic() - started) / 60
    print(
        f"\nFertig in {elapsed_min:.1f} min: {ok} indexiert, {skipped} übersprungen, "
        f"{failed} fehlgeschlagen, {chunks_total} Chunks gesamt."
    )
    return 0 if failed == 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())
