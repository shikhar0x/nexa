from dataclasses import dataclass
import os


@dataclass
class Settings:
    """Global configuration settings for Nexa."""
    llm_model: str = "llama3.2:3b"
    db_path: str = "nexa.db"
    chroma_path: str = "chroma_data"
    search_max_seconds: float = 5.0
    search_max_results: int = 20
    log_file: str = os.path.join("logs", "nexa.log")
    log_level: str = "INFO"
    pending_action_timeout: float = 120.0
    working_directory_timeout: float = 300.0
    debug: bool = os.getenv("NEXA_DEBUG", "0").lower() in ("1", "true", "yes")


settings = Settings()

