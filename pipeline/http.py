"""HTTP helper with an on-disk cache and retries.

The raw responses are cached in ``data_cache/`` (git-ignored), so changing a
calculation and re-running the pipeline doesn't download anything again.

Most sources answer JSON; the IMF, Philadelphia Fed, Fed Board, NY Fed and
Treasury files are Excel or CSV. Each format has a cheap check that the body
really is that kind of file, so an HTML error page answered with status 200
(a bot wall, a maintenance page) is retried and never cached.
"""

from __future__ import annotations

import atexit
import hashlib
import json
import os
import sys
import time
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote

import httpx

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = Path(os.environ.get("IFR_CACHE_DIR", ROOT / "data_cache"))
USER_AGENT = "forecasts-vs-reality/0.1 (build-time data loader; python-httpx)"

# Rate limiting and transient server errors are worth retrying.
RETRY_STATUS = {429, 500, 502, 503, 504}


def log(*args: object) -> None:
    print(*args, file=sys.stderr, flush=True)


def _is_json(data: bytes) -> bool:
    try:
        json.loads(data)
    except ValueError:
        return False
    return True


def _is_csv(data: bytes) -> bool:
    head = data[:200].lstrip().lower()
    return bool(head) and not head.startswith((b"<", b"{", b"["))


# format -> (body check, cache file suffix, Accept header)
FORMATS = {
    "json": (_is_json, ".json", "application/json"),
    "xlsx": (lambda b: b[:2] == b"PK", ".xlsx", "*/*"),  # a zip archive
    "xls": (lambda b: b[:8] == bytes.fromhex("d0cf11e0a1b11ae1"), ".xls", "*/*"),  # OLE2 compound file
    "csv": (_is_csv, ".csv", "text/csv,*/*"),
}


def _cache_path(url: str, params: dict | None, fmt: str = "json") -> Path:
    key = url + "?" + "&".join(f"{k}={v}" for k, v in sorted((params or {}).items()))
    return CACHE_DIR / f"{hashlib.sha256(key.encode()).hexdigest()[:20]}{FORMATS[fmt][1]}"


def cached_path(url: str, params: dict | None = None, fmt: str = "json") -> Path | None:
    """Where ``fetch`` stored this request, or None if it was never downloaded. Ignores ``max_age``."""
    path = _cache_path(url, params, fmt)
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
        _client = httpx.Client(follow_redirects=True, headers={"User-Agent": USER_AGENT})
        atexit.register(_client.close)
    return _client


class BadBody(Exception):
    """A 200 response whose body isn't the expected format."""


def fetch(
    url: str,
    *,
    params: dict | None = None,
    max_age: timedelta | None = timedelta(hours=12),
    retries: int = 5,
    timeout: float = 300.0,
    fmt: str = "json",
) -> bytes:
    """GET ``url`` and return the body, using the disk cache when fresh. ``max_age=None`` caches forever.

    ``fmt`` is the expected body format (see ``FORMATS``). SGS sometimes answers
    200 with an empty body or an HTML "Requisição inválida" page, which goes away
    on retry, so a body of the wrong format is retried and never cached.
    """
    valid, _, accept = FORMATS[fmt]
    path = _cache_path(url, params, fmt)
    if path.exists() and (max_age is None or time.time() - path.stat().st_mtime < max_age.total_seconds()):
        data = path.read_bytes()
        if valid(data):
            return data
        log(f"  discarding invalid cached response for {url}")

    full = full_url(url, params)
    delay = 2.0
    for attempt in range(1, retries + 1):
        try:
            resp = _get_client().get(full, timeout=timeout, headers={"Accept": accept})
            if resp.status_code in RETRY_STATUS:
                raise httpx.HTTPStatusError(f"{resp.status_code}", request=resp.request, response=resp)
            if resp.is_error:
                # Other 4xx won't get better on retry.
                raise RuntimeError(f"{resp.status_code} for {full}: {resp.text[:300]}")
            data = resp.content
            if not valid(data):
                raise BadBody(f"not {fmt}: body ({resp.headers.get('content-type')}, {len(data)} bytes): {data[:100]!r}")
            break
        except (httpx.TransportError, httpx.HTTPStatusError, BadBody) as exc:
            if attempt == retries:
                raise RuntimeError(f"{full}: {exc}") from exc
            log(f"  retry {attempt}/{retries} for {url} in {delay:.0f}s ({exc})")
            time.sleep(delay)
            delay *= 2

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    tmp.write_bytes(data)
    tmp.replace(path)
    return data
