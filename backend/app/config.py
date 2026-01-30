"""
Configuration module for FastAPI backend.
Loads environment variables for Supabase, external APIs, and LLM.
"""

import os
from typing import Optional


class Settings:
    """
    Application settings loaded from environment variables.
    Following CLAUDE.md: secrets are injected via environment, never hardcoded.
    """

    # Supabase Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")

    # External Enrichment APIs (check both uppercase and mixed case)
    APOLLO_API_KEY: Optional[str] = os.getenv("APOLLO_API_KEY") or os.getenv("Apollo_API_KEY")
    PDL_API_KEY: Optional[str] = os.getenv("PDL_API_KEY") or os.getenv("Pdl_API_KEY")
    HUNTER_API_KEY: Optional[str] = os.getenv("HUNTER_API_KEY") or os.getenv("Hunter_API_KEY")
    TAVILY_API_KEY: Optional[str] = os.getenv("TAVILY_API_KEY") or os.getenv("Tavily_API_KEY")
    ZOOMINFO_API_KEY: Optional[str] = os.getenv("ZOOMINFO_API_KEY") or os.getenv("ZoomInfo_API_KEY")
    GNEWS_API_KEY: Optional[str] = os.getenv("GNEWS_API_KEY") or os.getenv("GNews_API_KEY")

    # LLM Configuration (multi-provider with fallback)
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    LLM_MODEL: str = "claude-3-5-haiku-20241022"  # Fast, cost-effective
    LLM_TIMEOUT: int = 30  # seconds (target <60s end-to-end)

    # App Configuration
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    MOCK_MODE: bool = os.getenv("MOCK_SUPABASE", "false").lower() == "true"

    def validate(self) -> None:
        """Validate that required settings are present (skip in mock mode)."""
        if self.MOCK_MODE:
            return  # Mock mode doesn't require real credentials
        required = ["SUPABASE_URL", "SUPABASE_KEY"]
        missing = [k for k in required if not getattr(self, k, None)]
        if missing:
            raise ValueError(f"Missing required environment variables: {missing}")


settings = Settings()
