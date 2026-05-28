"""
pdf_loader_pymupdf.py – PDF-Textextraktion mit PyMuPDF (fitz).

Implementiert das DocumentLoader-Protokoll. Extrahiert Text direkt aus der PDF-Struktur
ohne OCR – gescannte PDFs ohne eingebetteten Text liefern leere Seiten.
"""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF – Paketname "pymupdf", Importname "fitz"

from app.core.types import RawDocument, RawDocumentPage
from app.core.utils import sha256_file


class PDFLoader:
    """Lädt eine PDF-Datei und gibt ein RawDocument mit seitenweisem Text zurück."""

    def load(self, file_path: Path) -> RawDocument:
        """
        Berechnet zuerst den SHA-256-Hash der Datei, liest dann alle Seiten aus
        und gibt sie als RawDocument zurück. Der finally-Block stellt sicher,
        dass das Datei-Handle auch bei Fehlern geschlossen wird.
        """
        doc_hash = sha256_file(file_path)  # Fingerabdruck vor dem Öffnen berechnen
        doc = fitz.open(file_path)

        pages: list[RawDocumentPage] = []
        try:
            for i in range(doc.page_count):
                page = doc.load_page(i)
                text = page.get_text("text") or ""  # "text" = reiner Fließtext ohne Formatierung
                pages.append(RawDocumentPage(page_number=i + 1, text=text))  # i+1: fitz ist 0-basiert
        finally:
            doc.close()  # immer schließen, auch bei Exception

        return RawDocument(source_path=str(file_path), doc_hash=doc_hash, pages=pages)
