"""HTTP helper with an on-disk cache and retries.

The raw API responses are cached in ``data_cache/`` (git-ignored), so changing a
calculation and re-running the pipeline doesn't hit the Banco Central again.
"""

from __future__ import annotations

import atexit
import hashlib
import os
import sys
import time
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote

import httpx

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = Path(os.environ.get("IFR_CACHE_DIR", ROOT / "data_cache"))
USER_AGENT = "inflation-forecasts-vs-reality/0.1 (build-time data loader; python-httpx)"

# Rate limiting and transient server errors are worth retrying.
RETRY_STATUS = {429, 500, 502, 503, 504}


def log(*args: object) -> None:
    print(*args, file=sys.stderr, flush=True)


def _cache_path(url: str, params: dict | None) -> Path:
    key = url + "?" + "&".join(f"{k}={v}" for k, v in sorted((params or {}).items()))
    return CACHE_DIR / f"{hashlib.sha256(key.encode()).hexdigest()[:20]}.json"


def cached_path(url: str, params: dict | None = None) -> Path | None:
    """Where ``fetch`` stored this request, or None if it was never downloaded. Ignores ``max_age``."""
    path = _cache_path(url, params)
    return path if path.exists() else None


def full_url(url: str, params: dict | None = None) -> str:
    """The URL ``fetch`` requests. Spaces are encoded as %20 here: Olinda's OData
    parser answers 400 to the "+" httpx would send."""
    return url + ("?" + "&".join(f"{quote(k)}={quote(str(v), safe=',')}" for k, v in params.items()) if params else "")


_client: httpx.Client | None = None


def _get_client() -> httpx.Client:
    """One client per process, so consecutive requests to the same host reuse the
    TLS connection (the 10-year SGS windows, one Olinda query per indicator)."""
    global _client
    if _client is None:
        _client = httpx.Client(follow_redirects=True, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        atexit.register(_client.close)
    return _client


def fetch(
    url: str,
    *,
    params: dict | None = None,
    max_age: timedelta | None = timedelta(hours=12),
    retries: int = 5,
    timeout: float = 300.0,
) -> bytes:
    """GET ``url`` and return the body, using the disk cache when fresh. ``max_age=None`` caches forever."""
    path = _cache_path(url, params)
    if path.exists() and (max_age is None or time.time() - path.stat().st_mtime < max_age.total_seconds()):
        return path.read_bytes()

    full = full_url(url, params)
    delay = 2.0
    for attempt in range(1, retries + 1):
        try:
            resp = _get_client().get(full, timeout=timeout)
            if resp.status_code in RETRY_STATUS:
                raise httpx.HTTPStatusError(f"{resp.status_code}", request=resp.request, response=resp)
            if resp.is_error:
                # Other 4xx won't get better on retry.
                raise RuntimeError(f"{resp.status_code} for {full}: {resp.text[:300]}")
            data = resp.content
            break
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            if attempt == retries:
                raise
            log(f"  retry {attempt}/{retries} for {url} in {delay:.0f}s ({exc})")
            time.sleep(delay)
            delay *= 2

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    tmp.write_bytes(data)
    tmp.replace(path)
    return data
