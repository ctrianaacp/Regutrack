"""Shared async HTTP client with retry logic and rate limiting."""

import asyncio
import logging
import random
from typing import Optional

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from regutrack.config import settings

logger = logging.getLogger(__name__)

# Default headers that look like a real browser
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Domain-level rate limiting: tracks last request time per host
_last_request_time: dict[str, float] = {}
_rate_lock = asyncio.Lock()


async def _respect_delay(host: str) -> None:
    """Ensure minimum delay between requests to the same host."""
    async with _rate_lock:
        loop = asyncio.get_event_loop()
        now = loop.time()
        last = _last_request_time.get(host, 0.0)
        wait = settings.scraper_request_delay - (now - last)
        if wait > 0:
            await asyncio.sleep(wait + random.uniform(0, 0.5))
        _last_request_time[host] = loop.time()


async def fetch_html(
    url: str,
    headers: Optional[dict] = None,
    params: Optional[dict] = None,
    timeout: Optional[int] = None,
) -> str:
    """
    Fetch a URL and return the response text.
    Handles retries, rate limiting per domain, and timeouts.
    """
    merged_headers = {**DEFAULT_HEADERS, **(headers or {})}
    _timeout = timeout or settings.scraper_timeout

    # Extract host for per-domain rate limiting
    from urllib.parse import urlparse
    host = urlparse(url).netloc

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=_timeout,
        headers=merged_headers,
        verify=False,  # Some .gov.co sites have SSL issues
        proxy=settings.scraper_proxy_url if settings.scraper_proxy_url else None,
    ) as client:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(settings.scraper_max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=15),
            retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
            reraise=True,
        ):
            with attempt:
                await _respect_delay(host)
                logger.debug(f"GET {url}")
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.text

    raise RuntimeError(f"Failed to fetch {url} after retries")


async def fetch_json(
    url: str,
    headers: Optional[dict] = None,
    params: Optional[dict] = None,
    timeout: Optional[int] = None,
) -> dict | list:
    """Fetch a URL and parse JSON response."""
    merged_headers = {**DEFAULT_HEADERS, **(headers or {}), "Accept": "application/json"}
    _timeout = timeout or settings.scraper_timeout

    from urllib.parse import urlparse
    host = urlparse(url).netloc

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=_timeout,
        headers=merged_headers,
        verify=False,
        proxy=settings.scraper_proxy_url if settings.scraper_proxy_url else None,
    ) as client:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(settings.scraper_max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=15),
            retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
            reraise=True,
        ):
            with attempt:
                await _respect_delay(host)
                logger.debug(f"GET JSON {url}")
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()

    raise RuntimeError(f"Failed to fetch JSON from {url} after retries")
