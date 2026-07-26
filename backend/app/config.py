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

    # Admin
    admin_api_key: str = "dart0s-admin-2024"

    # Groq LLM (free tier, primary LLM provider)
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_ambiguity_model: str = "llama-3.1-8b-instant"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # Cerebras LLM (fallback — requires billing)
    cerebras_api_key: str = ""
    cerebras_model: str = "gpt-oss-120b"
    cerebras_base_url: str = "https://api.cerebras.ai/v1"

    # Ambiguous disclosure threshold: scores below this get Cerebras analysis
    # when keyword matching is insufficient (category=OTHER or ambiguous titles)
    cerebras_analysis_threshold: int = 40

    # Supabase
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_anon_key: str = ""

    # JWT (supplemental; Supabase Auth is primary)
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"

    # Polling
    poll_interval_seconds: int = 30

    # Scoring & visibility
    feed_visibility_threshold: int = 80  # disclosures with score >= this go to /live
    free_tier_delay_seconds: int = 180   # 3-minute delay for free/anonymous users

    # Valid categories (canonical list)
    categories: List[str] = [
        "ADMINISTRATIVE",
        "CAPITAL_RAISING",
        "BIOTECH",
        "BUSINESS_CONTRACT",
        "EARNINGS",
        "SHAREHOLDER_RETURN",
        "DELISTING_RISK",
        "OTHER",
    ]

    @property
    def cors_origin_list(self) -> List[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",")]

    model_config = {"env_file": ".env", "case_sensitive": False, "extra": "ignore"}


settings = Settings()
