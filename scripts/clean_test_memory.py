#!/usr/bin/env python3
"""Remove test-harness exchanges ('Mocked response') from Nexa's real memory.

Before tests/conftest.py existed, running the test suite persisted fixture
exchanges into the developer's real nexa.db and chroma_data — small models
then regurgitated 'Mocked response' in live chat. Run once to heal it:

    python3 scripts/clean_test_memory.py

Idempotent: exits quietly when there is nothing to clean.
"""
import os
import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("NEXA_DB_PATH", str(REPO / "nexa.db")))
CHROMA_PATH = os.getenv("NEXA_CHROMA_PATH", str(REPO / "chroma_data"))

POISON_CONTENT = "Mocked response"


def main() -> None:
    if not DB_PATH.exists():
        print(f"No memory database at {DB_PATH} — nothing to clean.")
        return

    conn = sqlite3.connect(str(DB_PATH))
    ids = [row[0] for row in conn.execute(
        "SELECT id FROM messages WHERE content = ?", (POISON_CONTENT,)
    )]
    if ids:
        placeholders = ",".join("?" for _ in ids)
        conn.execute(f"DELETE FROM messages WHERE id IN ({placeholders})", ids)
        conn.execute(f"DELETE FROM memory_embeddings WHERE msg_id IN ({placeholders})", ids)
        conn.commit()
    total_after = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    conn.close()

    if not ids:
        print(f"Clean already: no '{POISON_CONTENT}' rows in {DB_PATH} ({total_after} messages kept).")
    else:
        print(f"Removed {len(ids)} poisoned message(s) from {DB_PATH} ({total_after} messages kept).")

        # Their vector embeddings must go too, or retrieval can still surface them.
        chroma_dir = Path(CHROMA_PATH)
        if chroma_dir.exists():
            try:
                import chromadb
                client = chromadb.PersistentClient(path=str(chroma_dir))
                col = client.get_collection(name="nexa_memory")
                col.delete(ids=[str(i) for i in ids])
                print(f"Removed {len(ids)} embedding(s) from ChromaDB at {chroma_dir}.")
            except Exception as e:
                print(f"warning: could not clean ChromaDB embeddings: {e}")
                print("If answers still echo test text, delete the chroma_data/ folder — it rebuilds lazily.")
        else:
            print("No chroma_data folder found — vector store will rebuild lazily from clean data.")


if __name__ == "__main__":
    main()
