"""Configuration management using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="sqlite:///./regutrack.db",
        description="SQLAlchemy database URL",
    )

    # Scraper
    scraper_request_delay: float = Field(
        default=2.0, description="Seconds between requests to the same domain"
    )
    scraper_max_retries: int = Field(default=3, description="Max retries per request")
    scraper_timeout: int = Field(default=30, description="Request timeout in seconds")
    scraper_use_playwright: bool = Field(
        default=True, description="Enable Playwright for JS-rendered sites"
    )

    # Scheduler
    scheduler_hour: int = Field(default=6, description="Hour of first run (24h, legacy)")
    scheduler_minute: int = Field(default=0, description="Minute of first run (legacy)")
    scheduler_interval_hours: int = Field(
        default=6, description="Run scrapers every N hours (default: every 6h)"
    )

    # Notifications
    notifier_webhook_url: str = Field(default="", description="Webhook URL for alerts")
    notifier_smtp_host: str = Field(default="", description="SMTP host")
    notifier_smtp_port: int = Field(default=587, description="SMTP port")
    notifier_smtp_user: str = Field(default="", description="SMTP username")
    notifier_smtp_pass: str = Field(default="", description="SMTP password")
    notifier_email_from: str = Field(default="", description="From email address")
    notifier_email_to: str = Field(default="", description="To email address")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_dir: str = Field(default="logs", description="Directory for log files")

    # ── AI / Adaptive Scraper ──────────────────────────────────────────────
    # Disabled by default. Set AI_SCRAPER_ENABLED=true and OPENAI_API_KEY in .env
    # to activate the OpenAI fallback extraction when a scraper returns 0 docs.
    ai_scraper_enabled: bool = Field(
        default=False,
        description="Enable AI-powered fallback extraction when scraper returns 0 docs",
    )
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key (required when ai_scraper_enabled=true)",
    )
    ai_model: str = Field(
        default="gpt-4o",
        description="OpenAI model for AI extraction (e.g. gpt-4o, o3-mini).",
    )
    ai_max_html_chars: int = Field(
        default=80_000,
        description="Max HTML characters to send to the LLM (truncated to avoid token limits)",
    )
    ai_dom_fingerprint_enabled: bool = Field(
        default=False,
        description="Enable predictive DOM structure change detection",
    )


# Singleton instance
settings = Settings()

