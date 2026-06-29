import traceback
from app.core.types import RawDocument, Chunk

class RecursiveTextChunker:
    def __init__(self, *args, **kwargs):
        pass
        
    def chunk(self, doc: RawDocument) -> list[Chunk]:
        print("🕵️ CHUNKER SPION 1: Chunker wurde erfolgreich aufgerufen!")
        chunks = []
        
        try:
            for page in doc.pages:
                lines = page.text.splitlines()
                print(f"🕵️ CHUNKER SPION 2: Versuche {len(lines)} Zeilen umzuwandeln...")
                
                for i, line in enumerate(lines):
                    if line.strip(): 
                        try:
                            # Hier passiert höchstwahrscheinlich der stille Crash!
                            chunk_obj = Chunk(
                                text=line,
                                source_path=doc.source_path,
                                page_number=page.page_number,
                                position=i,
                                doc_hash=doc.doc_hash
                            )
                            chunks.append(chunk_obj)
                        except Exception as inner_e:
                            print(f"\n🧨 CRASH BEIM CHUNK-BAUEN (Zeile {i}): {repr(inner_e)}")
                            print("🚨 VERDACHT: Die Parameter passen nicht zu deiner types.py!\n")
                            return [] # Wir brechen hier ab, damit du den Fehler im Terminal siehst!
                            
            print(f"🕵️ CHUNKER SPION 3: {len(chunks)} Chunks erfolgreich gebaut!")
        except Exception as e:
            print(f"\n🧨 KRITISCHER CHUNKER FEHLER:\n{traceback.format_exc()}\n")
            
        return chunks
