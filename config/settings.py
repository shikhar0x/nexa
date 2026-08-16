from dataclasses import dataclass
import os


@dataclass
class Settings:
    """Global configuration settings for Nexa."""
    llm_model: str = "phi4-mini"
    db_path: str = "nexa.db"
    chroma_path: str = "chroma_data"
    search_max_seconds: float = 5.0
    search_max_results: int = 20
    log_file: str = os.path.join("logs", "nexa.log")
    log_level: str = "INFO"
    pending_action_timeout: float = 120.0
    working_directory_timeout: float = 300.0
    temperature: float = 0.2  # Low randomness: keep answers grounded in real data
    num_ctx: int = 4096  # Context window for the local model (tuned for CPU laptops)
    history_limit: int = 2  # Recent conversation turns sent to the model (fewer = faster)
    memory_context_max_chars: int = 1200  # Cap on injected memory context (fewer = faster)
    memory_min_messages_for_search: int = 20  # Below this, vector search is skipped (no embeddings)
    memory_context_recent_turns: int = 2  # Recent turns injected as context when vector search is skipped
    classification_max_tokens: int = 64  # Cap on the intent-classification reply (JSON is short)
    deterministic_system_report: bool = True  # Print system/OS/network info as an instant pre-formatted report (no LLM)
    debug: bool = os.getenv("NEXA_DEBUG", "0").lower() in ("1", "true", "yes")


settings = Settings()

