# Nexa — Local-First AI Desktop Companion

Nexa is a privacy-focused, local-first AI desktop companion featuring persistent memory across process restarts, natural language intent routing, desktop system monitoring, document text extraction, native token streaming, safe command execution, and a modular skill-based architecture.

---

## Key Features

- 🧠 **Persistent Cross-Session Memory & CQRS Control**: Retains facts and context across restarts using SQLite for raw turn logging and ChromaDB for vector semantic search. Factual memory queries (`MEMORY_STATS`, `MEMORY_EXPORT`, `MEMORY_DELETE`, `MEMORY_CLEAR`) bypass the LLM deterministically (`use_llm=False`), eliminating hallucinations.
- ⚡ **Native Token Streaming**: Real-time token streaming powered by Ollama's `stream=True` API and a dedicated `ConsoleRenderer` (`runtime/renderer.py`), providing responsive CLI output without screen redrawing.
- 📄 **Document & Code Intelligence (`FileReaderSkill`)**: Extracts text from PDFs (`PyPDF2`), text documents, Markdown, JSON, CSV, and source code files (`.py`, `.js`, `.ts`, `.c`, `.cpp`, `.java`), safely feeding content to the LLM for reasoning.
- 📍 **Workspace State Context**: Maintains lightweight conversation context (`workspace_state["active_file"]`) across turns so follow-up commands (*"summarize it"*, *"open it"*, *"search inside this file"*) work naturally.
- 🧩 **Modular Skill Architecture**: Decoupled intent routing and skill registry (`skills/`) allowing new capabilities to be added without modifying core runtime code.
- 💻 **Desktop System Integration**:
  - **System Health**: Monitor CPU, RAM, disk, battery, and hardware stats in conversational language.
  - **File Intelligence**: Search files by filename, search inside text files via `ripgrep`, and perform targeted document search.
  - **Desktop Notifications & Reminders**: Timed reminders delivered via native OS notification systems (`notify-send`).
- 🛡️ **Safety Gate**: All OS-modifying actions (opening applications, running shell commands, clearing memory) pass through explicit user confirmation (`confirm_action`).
- 🛑 **Deterministic Error Handling**: Factual error responses on system operation failures prevent the LLM from fabricating excuses.
- 🖥️ **OS Abstraction Layer**: Clean OS-independent interface (`infrastructure/os/`) isolating operating system calls.
- 📝 **Structured Logging & Testing**: Configurable settings (`config/settings.py`), structured logging (`logs/nexa.log`), and 121 automated unit tests across 13 test files (`tests/`).

---

## Project Architecture

```text
nexa/
├── main.py                     # Minimal CLI loop
├── config/
│   ├── settings.py             # Settings (models, paths, timeouts)
│   ├── constants.py            # System keywords & prompt templates
│   └── logger.py               # Centralized logging setup
├── runtime/
│   ├── context.py              # ConversationContext DTO & workspace_state
│   ├── dispatcher.py           # Central runtime orchestrator
│   ├── intent.py               # Decoupled IntentRouter & IntentResult DTO
│   ├── llm.py                  # LLMEngine accepting ConversationContext & streaming
│   └── renderer.py             # ConsoleRenderer for live token streaming
├── skills/
│   ├── base.py                 # BaseSkill & standardized SkillResult DTO (use_llm flag)
│   ├── path_resolver.py        # Shared unified path resolver & working directory context
│   ├── registry.py             # SkillRegistry with alias support
│   ├── system_status.py        # SystemStatusSkill
│   ├── file_reader.py          # FileReaderSkill (PDF, text, markdown, source code)
│   ├── file_search.py          # FileSearchSkill & FileContentSearchSkill (targeted search)
│   ├── memory_skill.py        # MemorySkill (CQRS stats, export, delete, clear, summarize)
│   ├── open_file.py            # OpenFileSkill (Confirmation gate)
│   ├── shell.py                # ShellExecutionSkill (Confirmation gate)
│   └── notification.py         # ReminderSkill
├── memory/
│   ├── service.py              # MemoryService facade with CQRS Read/Write API
│   ├── db.py                   # SQLite conversation log
│   ├── vector_store.py         # ChromaDB persistence & ephemeral client test helper
│   └── retrieval.py            # Vector memory context retrieval
├── infrastructure/
│   ├── scheduler.py            # Threaded Scheduler service
│   ├── security.py             # Confirmation gate (confirm_action)
│   ├── monitor.py              # System stats & hardware sensors provider
│   ├── notifications.py        # Desktop notification helper
│   ├── search/
│   │   └── oswalk.py           # File, ripgrep, and PDF search backend
│   └── os/
│       ├── base.py             # BaseOSAdapter abstract class
│       ├── linux.py            # LinuxOSAdapter (xdg-open, notify-send)
│       └── factory.py          # OS adapter factory
├── logs/                       # Application logs (nexa.log)
└── tests/                      # Automated unit test suite (121 tests, 13 test modules)
```

---

## Prerequisites

- **Python 3.11+**
- **Ollama** running locally with `llama3.2:3b` model pulled:
  ```bash
  ollama pull llama3.2:3b
  ```
- **ripgrep** (optional, for fast file content searching):
  ```bash
  sudo apt install ripgrep
  ```

---

## Installation & Setup

1. **Clone or enter the directory:**
   ```bash
   cd nexa
   ```

2. **Set up virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## Usage

Run the main CLI loop:

```bash
python main.py
```

### Example Prompts

#### 1. System Monitoring
- `"how's my battery?"`
- `"what's my CPU usage like?"`
- `"show os version"`

#### 2. Document Reading & Summarization
- `"read report.pdf"`
- `"summarize report.pdf"`
- `"explain this document"`
- `"search inside report.pdf for executive summary"`

#### 3. Deterministic Memory Operations
- `"show memory stats"`
- `"export memory"`
- `"forget color"`
- `"clear memory"`
- `"summarize what you know about Python"`

#### 4. File & Content Search
- `"find DBMS files"`
- `"where is my report"`
- `"search inside files for TODO"`

#### 5. Reminders & Notifications
- `"remind me in 30 seconds to take a break"`
- `"remind me in 5 minutes to check the build"`

#### 6. Safe Action Execution (Requests Confirmation)
- `"open presentation.pdf"`
- `"run command ls -la"`

---

## Running Unit Tests

Run all 121 automated unit tests across 13 test modules:

```bash
python -m unittest discover -s tests -v
```

---

## Roadmap

- [x] **Phase 1 — Foundation**: SQLite conversation log + ChromaDB vector memory persistence + CQRS MemorySkill.
- [x] **Phase 2 — Desktop Integration & Runtime Stabilization**: System monitoring, file/PDF reader & search, native token streaming, notifications, safe action execution, workspace state working context, deterministic failure recovery, prompt regression suite.
- [ ] **Phase 3 — Developer Mode**: Git integration, repo indexing, watchdog file watching, build log analysis.
- [ ] **Phase 4 — Vision**: OCR, active window context, live screen understanding.
- [ ] **Phase 5 — Voice Interface**: STT (Whisper), TTS (Piper), wake-word detection.
- [ ] **Phase 6 — Intelligence Layer**: Habit learning and proactive context prediction.

---

## License

This project is licensed under the terms of the [MIT License](LICENSE).
