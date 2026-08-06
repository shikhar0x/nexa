# Nexa — Full Implementation Plan

Local-first AI desktop companion. Phased build, each phase depends on the previous one working before starting the next.

---

## Phase 1 — Foundation (Memory + Conversation Engine)

**Goal:** Prove persistent memory works across process restarts, not just in-context recall.

**Stack**
- Python 3.11+, venv
- Ollama running `llama3.2:1b` (upgrade later as hardware allows)
- `chromadb` for vector storage / semantic search
- `sqlite3` (stdlib) for structured conversation log

**Folder structure**
```
nexa/
├── venv/
├── memory/
│   ├── __init__.py
│   ├── db.py            # SQLite: raw conversation log
│   ├── vector_store.py  # Chroma: embeddings + semantic search
│   └── retrieval.py     # combines both, returns context for a query
├── engine/
│   ├── __init__.py
│   └── chat.py           # calls ollama.chat(), injects retrieved context
├── main.py                # CLI loop: input → retrieve → respond → store
├── nexa.db                 # SQLite file (created on first run)
└── chroma_data/              # Chroma's persistent store (created on first run)
```

**Setup**
```bash
mkdir nexa && cd nexa
python3 -m venv venv
source venv/bin/activate
pip install ollama chromadb
mkdir memory engine
touch memory/__init__.py engine/__init__.py
```

**`memory/db.py`**
```python
import sqlite3
from datetime import datetime

DB_PATH = "nexa.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def save_message(role, content):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO messages (role, content, timestamp) VALUES (?, ?, ?)",
        (role, content, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
```

**`memory/vector_store.py`**
```python
import chromadb

client = chromadb.PersistentClient(path="chroma_data")
collection = client.get_or_create_collection(name="nexa_memory")

def add_memory(text, msg_id):
    collection.add(
        documents=[text],
        ids=[str(msg_id)]
    )

def search_memory(query, top_k=3):
    results = collection.query(
        query_texts=[query],
        n_results=top_k
    )
    return results["documents"][0] if results["documents"] else []
```

**`memory/retrieval.py`**
```python
from memory.vector_store import search_memory

def get_context(query):
    relevant = search_memory(query)
    if not relevant:
        return ""
    return "Relevant past context:\n" + "\n".join(f"- {r}" for r in relevant)
```

**`engine/chat.py`**
```python
import ollama

def get_response(user_input, context=""):
    system_prompt = "You are Nexa, a personal assistant with persistent memory."
    if context:
        system_prompt += f"\n\n{context}"

    response = ollama.chat(
        model="llama3.2:1b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
    )
    return response["message"]["content"]
```

**`main.py`**
```python
from memory.db import init_db, save_message
from memory.vector_store import add_memory
from memory.retrieval import get_context
from engine.chat import get_response
import sqlite3

def get_last_id():
    conn = sqlite3.connect("nexa.db")
    cur = conn.execute("SELECT last_insert_rowid()")
    result = cur.fetchone()[0]
    conn.close()
    return result

def main():
    init_db()
    print("Nexa is running. Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break

        context = get_context(user_input)
        response = get_response(user_input, context)
        print(f"Nexa: {response}\n")

        save_message("user", user_input)
        user_id = get_last_id()
        add_memory(user_input, user_id)

        save_message("assistant", response)
        assist_id = get_last_id()
        add_memory(response, assist_id)

if __name__ == "__main__":
    main()
```

**Milestone test**
1. Run `python main.py`, tell it a fact/decision, `exit`.
2. Reopen `python main.py` (fresh process, fresh context window).
3. Ask about the fact. If it answers correctly, that's real persistent memory — not in-context recall.

**Known rough edges (acceptable at this stage)**
- Chroma's default embedding model is generic/small — fine for now, revisit if recall quality is weak.
- No conversation-length pruning yet.
- No fact-extraction layer — stores raw turns, not distilled facts. Refinement candidate once the loop is proven (call it Phase 1.5 if needed).

---

## Phase 2 — Desktop Integration

**Goal:** Nexa starts observing and doing things on the machine, with a hard safety gate on anything that changes system state.

**Additions**
- **System monitoring** — `psutil` for CPU, RAM, disk, battery, temperature. Report in plain language, not raw numbers (e.g. "RAM's getting tight, 92% used" instead of a bar chart).
- **File intelligence** — `os.walk` + `ripgrep` (via subprocess) for code/file search; `pdfplumber` or `PyPDF2` for PDF text search.
- **Command execution layer** — every OS-modifying action routes through a single `confirm_action()` gate before executing. No exceptions. This is the safety rail from your original doc's Module 4/12 — build it once, reuse everywhere.
- **Notifications** — simple desktop notifications (`notify2` on Linux) for reminders/alerts, no new infra needed.

**Structure addition**
```
nexa/
├── system/
│   ├── monitor.py     # psutil wrappers, human-readable summaries
│   ├── files.py        # search, locate, summarize
│   └── actions.py       # confirm_action() gate + actual executors
```

**Exit criteria for Phase 2:** You can ask "find my latest DBMS presentation" or "how's my battery" and get a real answer, and any action that touches the OS asks for confirmation first, every time, no silent execution.

---

## Phase 3 — Developer Mode

**Goal:** Reduce context-switching while coding — highest personal ROI phase since you're desk-bound coding daily.

**Additions**
- **Repo indexing** — walk directory tree, parse structure/imports, feed a summary into memory so Nexa "knows" the repo.
- **Git integration** — `GitPython` for status, diffs, branches, merge conflict detection.
- **Editor integration** — start with file-watching (`watchdog`) rather than a full VS Code extension; upgrade to the extension API later if needed.
- **Log/build analysis** — capture stdout/stderr from build/test commands, summarize errors in plain language instead of dumping raw tracebacks.
- **Code search** — reuse `ripgrep` from Phase 2, extend to function-level search.

**Exit criteria:** Nexa can tell you what branch you're on, whether there are unresolved conflicts, and explain a compiler error without you pasting it in manually.

---

## Phase 4 — Vision

**Goal:** Screen understanding — the most technically expensive phase, so it only starts once Phases 1–3 are stable and in daily use.

**Additions**
- **OCR** — Tesseract, or a small vision-capable local model if hardware allows.
- **Active window detection** — platform-specific (X11/Wayland tools on Linux).
- **PDF/document understanding** — extend Phase 2's file intelligence into live "what am I looking at" summaries.
- **UI element detection** — lowest priority sub-feature; likely deferred further even within this phase.

**Caution:** this phase has the highest risk of open-ended scope creep. Timebox it — if OCR + active-window context isn't reliably useful within a few weeks, cut UI detection and move on rather than perfecting it.

---

## Phase 5 — Voice Interface

**Goal:** Add voice as a UI layer on top of the already-working text pipeline — not a separate brain.

**Additions**
- **STT** — Faster-Whisper or whisper.cpp.
- **TTS** — Piper (lightweight, good for local-first).
- **Wake word** — Porcupine or openWakeWord for "Hey Nexa" detection.

**Structure:** voice input transcribes to text → feeds into the exact same `main.py` loop from Phase 1 → response gets piped to TTS instead of print(). No new conversation logic needed if Phase 1 was built cleanly.

---

## Phase 6 — Intelligence Layer

**Goal:** Habit learning and proactive suggestions — only makes sense with months of real usage data already sitting in the Phase 1 memory store.

**Additions**
- Pattern analysis over stored conversation/action history (preferred coding hours, frequently opened repos, common commands).
- Context prediction — surfacing likely-relevant info before being asked, based on what's open/active (ties back into Phase 4's vision layer).
- Explicit design constraint from the original vision doc: suggest, never assume. Nexa proposes, user confirms.

---

## Sequencing Notes

- **1 → 2 → 3** is the core value chain: memory that works, system integration that's safe, dev tools that save real time daily. This alone is a strong, demoable, resume-worthy tool — weeks of work, not months.
- **4 and 5** are the expensive phases (vision, audio pipelines). Don't start either until 1–3 are stable and genuinely in daily use — starting them early risks the same stall pattern as Ember/PCC/DSA running concurrently.
- **6** is data-dependent — it literally cannot be built well until Phases 1–3 have generated enough real history to learn from.
- If at any point a phase stalls for more than a few weeks without forward motion, that's the signal to stop, assess, and either simplify scope or shelve it — same rule that applies to every other open loop.
