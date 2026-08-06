# Nexa — Local-First AI Desktop Companion

Nexa is a privacy-focused, local-first AI desktop companion featuring persistent memory across process restarts, natural language intent routing, desktop system monitoring, safe command execution, and a modular skill-based architecture.

---

## Key Features

- 🧠 **Persistent Cross-Session Memory**: Retains facts and context across restarts using SQLite for raw turn logging and ChromaDB for vector semantic search.
- ⚡ **Local LLM Integration**: Powered by Ollama (`llama3.2:1b`) running 100% locally on your machine.
- 🧩 **Modular Skill Architecture**: Decoupled intent routing and skill registry (`skills/`) allowing new capabilities to be added without modifying runtime core code.
- 💻 **Desktop System Integration**:
  - **System Health**: Monitor CPU, RAM, disk, battery, and temperature in plain conversational language.
  - **File Intelligence**: Search files by filename, search inside text files via `ripgrep`, and search PDF contents via `PyPDF2`.
  - **Desktop Notifications & Reminders**: Timed reminders delivered via native OS notification systems (`notify-send`).
- 🛡️ **Safety Gate**: All OS-modifying actions (opening applications, running shell commands) pass through explicit user confirmation (`confirm_action`).
- 🖥️ **OS Abstraction Layer**: Clean OS-independent interface (`infrastructure/os/`) isolating operating system calls.
- 📝 **Structured Logging & Testing**: Configurable settings (`config/settings.py`), logging to `logs/nexa.log`, and built-in unit tests (`tests/`).

---

## Project Architecture

```text
nexa/
├── main.py                     # Minimal CLI loop (~25 lines)
├── config/
│   ├── settings.py             # Settings (models, paths, timeouts)
│   ├── constants.py            # System keywords & prompt templates
│   └── logger.py               # Centralized logging setup
├── runtime/
│   ├── context.py              # ConversationContext object
│   ├── dispatcher.py           # Central runtime orchestrator
│   ├── intent.py               # Decoupled IntentRouter & IntentResult DTO
│   └── llm.py                  # LLM engine accepting ConversationContext
├── skills/
│   ├── base.py                 # BaseSkill & standardized SkillResult DTO
│   ├── registry.py             # SkillRegistry for plugin management
│   ├── system_status.py        # SystemStatusSkill
│   ├── file_search.py          # FileSearchSkill & FileContentSearchSkill
│   ├── open_file.py            # OpenFileSkill (Confirmation gate)
│   ├── shell.py                # ShellExecutionSkill (Confirmation gate)
│   └── notification.py         # ReminderSkill
├── memory/
│   ├── service.py              # MemoryService facade
│   ├── db.py                   # SQLite conversation log
│   ├── vector_store.py         # ChromaDB persistence
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
└── tests/                      # Automated unit test suite
```

---

## Prerequisites

- **Python 3.11+**
- **Ollama** running locally with `llama3.2:1b` model pulled:
  ```bash
  ollama pull llama3.2:1b
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
   pip install ollama chromadb psutil PyPDF2
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
- `"how is my system doing?"`

#### 2. File & Content Search
- `"find my latest DBMS presentation"`
- `"where is my report"`
- `"search inside files for TODO"`

#### 3. Reminders & Notifications
- `"remind me in 30 seconds to take a break"`
- `"remind me in 5 minutes to check the build"`

#### 4. Safe Action Execution (Requests Confirmation)
- `"open /home/user/Desktop/nexa/main.py"`
- `"run command ls -la"`

#### 5. Persistent Memory Recall
- `"remember that my favorite programming language is Python"`
- Restart `main.py`
- `"what is my favorite programming language?"`

---

## Running Unit Tests

Run all 18 automated unit tests:

```bash
python3 -m unittest discover -s tests
```

---

## Roadmap

- [x] **Phase 1 — Foundation**: SQLite conversation log + ChromaDB vector memory persistence.
- [x] **Phase 2 — Desktop Integration**: System monitoring, file/PDF search, notifications, safe action execution.
- [ ] **Phase 3 — Developer Mode**: Git integration, repo indexing, watchdog file watching, build log analysis.
- [ ] **Phase 4 — Vision**: OCR, active window context, live screen understanding.
- [ ] **Phase 5 — Voice Interface**: STT (Whisper), TTS (Piper), wake-word detection.
- [ ] **Phase 6 — Intelligence Layer**: Habit learning and proactive context prediction.

---

## License

MIT License
