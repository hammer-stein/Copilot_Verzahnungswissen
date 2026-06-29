import pandas as pd
import hashlib
import os
from app.core.types import RawDocument, RawDocumentPage

class TabularLoader:
    def __init__(self):
        self.encodings_to_try = ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']

    def load(self, file_path: str) -> RawDocument:
        df = None
        for enc in self.encodings_to_try:
            try:
                df = pd.read_csv(file_path, sep=None, engine='python', encoding=enc)
                print(f"Erfolg: {file_path} gelesen mit Kodierung '{enc}'")
                break
            except Exception as e:
                continue
                
        if df is None:
            raise ValueError("Konnte Datei nicht lesen.")

        text_lines = []
        for _, row in df.iterrows():
            row_text = ", ".join([f"{col}: {val}" for col, val in row.items() if pd.notna(val)])
            text_lines.append(row_text)
            
        full_text = "\n".join(text_lines)
        
        # --- DER SPION ---
        print(f"🕵️ LOADER SPION: DataFrame hat {df.shape[0]} Zeilen gefunden.")
        print(f"🕵️ LOADER SPION: Der Text ist {len(full_text)} Zeichen lang.")

        with open(file_path, "rb") as f:
            doc_hash = hashlib.sha256(f.read()).hexdigest()

        page = RawDocumentPage(page_number=1, text=full_text)
        return RawDocument(source_path=file_path, doc_hash=doc_hash, pages=[page])