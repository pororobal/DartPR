"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    app_name: str = "DART0s"
    app_version: str = "1.0.0"
    debug: bool = True
    cors_origins: str = "*"

    # OpenDART API
    opendart_api_key: str = ""
    dart_api_base_url: str = "https://opendart.fss.or.kr/api"

    # Groq LLM
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # Supabase
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_anon_key: str = ""

    # JWT (supplemental; Supabase Auth is primary)
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"

    # Polling
    poll_interval_seconds: int = 30

    @property
    def cors_origin_list(self) -> List[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",")]

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()
