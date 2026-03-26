"""ReguTrack AI — Adaptive scraping intelligence powered by Gemini 2.5 Pro.

Components:
  - LLMExtractor:    Extracts documents from arbitrary HTML using Gemini
  - SelectorStore:   Persists/loads AI-learned CSS selectors per entity
  - HealthMonitor:   Detects DOM structural changes before scrapers break

All components respect the `ai_scraper_enabled` feature flag.
When disabled, zero API calls are made.
"""
