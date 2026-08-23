# Nexa — Local-First AI Desktop Companion

Nexa is a privacy-focused, local-first AI desktop companion with persistent memory, **hybrid intent routing** (deterministic rulebook → supervised LLM fallback), desktop monitoring, document extraction, token streaming, safe command execution, **developer-mode tooling** (git, repository indexing, file watching, build-log analysis), and a modular skill architecture. Everything runs locally with a single Ollama model.

---

## Key Features

- 🧠 **Persistent Cross-Session Memory (lazy vector sync)**: Conversation turns are stored in SQLite; ChromaDB semantic embeddings are synced in one batch only when memory is queried. This avoids per-turn embedding cost. Vector search degrades gracefully when the embedding backend is unreachable (offline), so a turn never crashes on memory retrieval.
- 🎯 **Hybrid Intent Routing**: A deterministic keyword rulebook (`config/constants.py`) handles common and safety-critical phrases with zero model calls. Other requests use a supervised JSON-mode LLM fallback against the capability index (`config/capabilities.py`). Destructive intents (`POWER_CONTROL`, `RUN_COMMAND`, `MEMORY_CLEAR`, `MEMORY_DELETE`, `MEMORY_EXPORT`, and `WIFI_CONTROL`) are keyword-only and can never be LLM-triggered.
- ⚡ **Instant Deterministic Reports**: System health, OS, and network reports use zero model calls by default (`deterministic_system_report: True`). Disable it to have the LLM interpret the data conversationally.
- 🗣️ **Small-Talk Fast Path**: Greetings, thanks, and capability questions are answered directly, avoiding a classification call.
- 🛠️ **Developer Mode**: Git integration (status, branch, diff, log, staging, commits, checkouts — all mutations confirmation-gated), repository indexing (“what does this project do?” — structure, entry point, tech stack, README summary), build-log and error explanation (grounded strictly in the actual error text, truncated to fit the model), and in-session file watching with desktop notifications (“watch this folder”).
- 📄 **Document & Code Intelligence (`FileReaderSkill`)**: Reads PDFs (`pypdf`), text, Markdown, JSON, CSV, and source files (`.py`, `.js`, `.ts`, `.c`, `.cpp`, `.java`) for LLM reasoning.
- 📍 **Workspace State Context**: Retains `workspace_state["active_file"]`, enabling natural follow-ups such as *“summarize it”*, *“open it”*, and *“search inside this file”*.
- 🧩 **Modular Skill Architecture**: Intent routing and the skill registry (`skills/`) are decoupled, so new capabilities do not require core runtime changes.
- 💻 **Desktop System Integration**: Health and hardware information; brightness, volume, Wi-Fi, and power controls; filename/content/document search; directory listing; reminders; screenshots; time & date; and CPU/RAM process insights.
- 🛡️ **Safety Gate**: Every OS-modifying action—including opening applications, shell commands, device or power controls, git mutations, and memory clearing—requires `confirm_action`.
- 🛑 **Deterministic Error Handling**: Factual error responses prevent fabricated explanations when system operations fail.
- 🖥️ **OS Abstraction Layer**: OS calls are isolated behind `infrastructure/os/`.
- 📝 **Structured Logging & Testing**: Configurable settings (`config/settings.py`), logs (`logs/nexa.log`), and 180+ automated tests (plus 50 JSON-driven regression subtests) across 25 test modules.

---

## Project Architecture

```text
nexa/
├── main.py                     # Minimal CLI loop
├── pytest.ini                  # Test warning filters (upstream deprecations)
├── config/
│   ├── settings.py             # Models, paths, timeouts, and speed knobs
│   ├── constants.py            # Keyword rulebook and system prompts
│   ├── capabilities.py         # Source of truth for LLM routing
│   └── logger.py               # Centralized logging
├── runtime/
│   ├── context.py              # ConversationContext DTO & workspace state
│   ├── dispatcher.py           # Runtime orchestrator
│   ├── intent.py               # Deterministic router & IntentResult DTO
│   ├── intent_hybrid.py        # Rulebook → LLM fallback → whitelist
│   ├── llm.py                  # Streaming and JSON-mode intent classification
│   └── renderer.py             # Live token renderer
├── skills/
│   ├── base.py                 # BaseSkill & SkillResult DTO
│   ├── registry.py             # Skill registry with aliases
│   ├── resolver.py             # CapabilityResolver aggregation
│   ├── system_status.py        # Deterministic system-health report
│   ├── os_info.py              # Deterministic OS report
│   ├── network_info.py         # Deterministic network report
│   ├── process_info.py         # Process insights
│   ├── directory_listing.py    # Directory listing
│   ├── path_resolver.py        # Filename/path resolution (active-file aware)
│   ├── file_reader.py          # PDF, text, Markdown, and source reader
│   ├── file_search.py          # Filename and content search
│   ├── memory_skill.py         # Memory stats, list, search, export, delete, clear
│   ├── open_file.py            # Confirmation-gated file opening
│   ├── shell.py                # Confirmation-gated shell execution
│   ├── notification.py         # Reminders
│   ├── git.py                  # Git status/diff/log/stage/commit/checkout
│   ├── repo_index.py           # Project structure and README summarizer
│   ├── build_log.py            # Build/test error explanation
│   ├── file_watch.py           # Directory watch → desktop notifications
│   ├── screenshot.py           # Screen capture
│   ├── time_date.py            # Time & date queries
│   ├── brightness.py / volume.py / wifi.py / power.py
│   └── unsupported.py          # UnsupportedCapabilitySkill
├── memory/
│   ├── service.py              # CQRS memory-service facade
│   ├── db.py                   # SQLite log + embedding tracker
│   ├── vector_store.py         # ChromaDB persistence and lazy sync
│   ├── retrieval.py            # Memory-context retrieval
│   └── facts.py                # Extracted user facts (name, preferences)
├── infrastructure/
│   ├── scheduler.py            # Threaded scheduler
│   ├── security.py             # Confirmation gate
│   ├── monitor.py              # System and hardware sensors
│   ├── notifications.py        # Desktop notification helper
│   ├── file_watcher.py         # Daemon-threaded watch sessions (watchfiles)
│   ├── search/oswalk.py        # File, ripgrep, and PDF search backend
│   └── os/                     # OS adapter interface (Linux, macOS)
├── logs/                       # Application logs
└── tests/                      # 180+ automated tests + JSON regression fixtures

```

## How Routing Works

```text
User prompt
    │
    ▼
1. Deterministic keyword rulebook (instant, 0 model calls)
    │  matched ────────────► skill executes
    │  GENERAL
    ▼
2. Small-talk / capability-question fast path (instant, 0 model calls)
    │  matched ────────────► general chat
    │  unmatched
    ▼
3. LLM fallback classification (one small call, JSON mode, ≤64 tokens)
    │  suggestion validated against capability-index whitelist
    │  safe & valid ──────► skill executes (arguments extracted deterministically)
    │  invalid / unsafe ──► general chat
```

Destructive intents are never LLM-suggestable and always require `confirm_action`. Arguments are extracted deterministically with regex and the path resolver, never by the model—so it can route requests but cannot fabricate paths, levels, or commands. Unseen phrasings work because the fallback maps requests against the capability index’s descriptions and examples.

## Prerequisites

- Python 3.11+
- Ollama, with the default model:

  ```bash
  ollama pull phi4-mini
  ```

- ripgrep (optional, for fast file-content search):

  ```bash
  sudo apt install ripgrep
  ```

To avoid the initial model-load delay, keep Ollama warm in RAM:

```bash
OLLAMA_KEEP_ALIVE=-1 ollama serve
```

For a permanent systemd configuration, run `sudo systemctl edit ollama` and add `Environment="OLLAMA_KEEP_ALIVE=-1"` under `[Service]`.

## Installation & Setup

```bash
cd nexa
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

## Example Prompts

### System Monitoring

- “how's my battery?”
- “what's my CPU usage like?”
- “let's start with my pc health.”
- “show os version” or “what's my ip?”
- “what's eating my ram?” or “why is my laptop slow?”

### Developer Mode

- “is my repo clean?”, “what branch am I on?”, “git diff”, or “recent commits”
- “add these files to git” or “git add skills/repo_index.py” (staging is confirmation-gated)
- “git add and commit: wire up routing” (stage + commit behind one confirmation)
- “what does this project do?” or “explain this codebase in ~/projects/foo”
- “why did the build fail?” or “explain the error in build.log”
- “watch this repo” → desktop notification on file changes; “what are you watching”; “stop watching”

### Document Reading & Summarization

- “read report.pdf”
- “summarize report.pdf”
- “what does this file say”
- “search inside report.pdf for executive summary”
- “which files contain sql”

### Deterministic Memory Operations

- “show memory stats” or “what do you remember”
- “export memory”
- “search memory for project goals”
- “forget color”
- “clear memory” or “erase all of your memory” (always confirmation-gated)
- “summarize what you know about Python”

### File & Content Search

- “find DBMS files” or “do you have any files about sql”
- “where is my report”
- “what's in my downloads”

### Reminders & Notifications

- “remind me in 30 seconds to take a break”
- “ping me in 5 minutes to stretch”

### Safe Actions

- “open presentation.pdf”
- “run command ls -la”
- “set brightness to 80%”, “make it louder”, or “kill the wifi”
- “shut it down” or “suspend my pc”

### Chat & Self-Knowledge

- “hey there!”, “thanks”, or “tell me a joke”
- “what can you do?” or “what are your skills?”

## Configuration

The main runtime knobs are in `config/settings.py`.

| Setting | Default | Purpose |
| --- | --- | --- |
| `llm_model` | `phi4-mini` | The single local model; `llama3.2:3b` also works well. |
| `temperature` | `0.2` | Low randomness keeps answers grounded in real data. |
| `num_ctx` | `4096` | Context window tuned for CPU laptops. |
| `history_limit` | `6` | Recent conversation turns sent to the model. |
| `memory_context_max_chars` | `1200` | Maximum injected memory-context length. |
| `memory_min_messages_for_search` | `20` | Below this, vector search is skipped. |
| `memory_context_recent_turns` | `2` | Recent turns used when vector search is skipped. |
| `classification_max_tokens` | `64` | Intent-classification JSON response cap. |
| `answer_max_tokens` | `200` | Conversational answer cap (keeps the model concise). |
| `deterministic_system_report` | `True` | Instant system/OS/network reports; `False` enables LLM interpretation. |
| `debug` | `NEXA_DEBUG` | Enables per-turn `[DEBUG TRACE]` instrumentation. |

## Running Unit Tests

```bash
python -m pytest tests/ -q
# or: python -m unittest discover -s tests -v
```

Key suites: `test_intent`, `test_hybrid_intent`, `test_prompt_regressions` (fixtures in `tests/prompts.json`), `test_pending_action`, `test_filename_resolution`, plus the Developer Mode suites `test_repo_index`, `test_git_add`, `test_build_log`, and `test_file_watch`.

---

## Roadmap

- [x] **Phase 1 — Foundation**: SQLite conversation log, ChromaDB vector-memory persistence, and CQRS `MemorySkill`.
- [x] **Phase 2 — Desktop Integration & Runtime Stabilization**: System monitoring, document reading/search, token streaming, notifications, safe actions, workspace state, deterministic failure recovery, and prompt regression tests.
- [x] **Speed & Comprehension Pass**: Hybrid routing, small-talk fast path, lazy ChromaDB embeddings, deterministic system reports, and CPU-oriented prompt-size tuning.
- [ ] **Phase 3 — Developer Mode**: Git integration, repository indexing, file watching, and build-log analysis.
- [ ] **Phase 4 — Vision**: OCR, active-window context, and live screen understanding.
- [ ] **Phase 5 — Voice Interface**: STT (Whisper), TTS (Piper), and wake-word detection.
- [ ] **Phase 6 — Intelligence Layer**: Habit learning and proactive context prediction.

---

## License
This project is licensed under the terms of the [MIT License](LICENSE).
