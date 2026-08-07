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


settings = Settings()
