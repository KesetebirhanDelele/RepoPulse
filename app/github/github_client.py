from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from typing import Any, Optional

import httpx

GITHUB_API = "https://api.github.com"

# Statuses that warrant a retry (transient server/infra errors + rate limits).
_RETRY_STATUSES = {429, 502, 503, 504}

# Statuses that are definitively terminal — never retry.
_NO_RETRY_STATUSES = {401, 404, 422}

_MAX_ATTEMPTS = 5
_BASE_BACKOFF_S = 0.5
_MAX_BACKOFF_S = 20.0
_MAX_SLEEP_S = 60.0

log = logging.getLogger(__name__)


def _is_rate_limit_403(resp: httpx.Response) -> bool:
    """Return True when a 403 looks like GitHub rate limiting rather than auth denial."""
    # Primary rate limit: X-RateLimit-Remaining == 0
    if resp.headers.get("X-RateLimit-Remaining") == "0":
        return True
    # Secondary rate limit: GitHub sets a Retry-After header
    if "Retry-After" in resp.headers:
        return True
    # Secondary rate limit body message
    try:
        body = resp.json()
        msg = (body.get("message") or "").lower()
        if "rate limit" in msg or "secondary rate" in msg:
            return True
    except Exception:
        pass
    return False


def _sleep_seconds(resp: httpx.Response, attempt: int) -> float:
    """Return how long to sleep before the next attempt."""
    # Explicit Retry-After header takes precedence.
    retry_after = resp.headers.get("Retry-After")
    if retry_after:
        try:
            return min(float(retry_after), _MAX_SLEEP_S)
        except ValueError:
            pass

    # Primary rate limit: sleep until reset time.
    remaining = resp.headers.get("X-RateLimit-Remaining")
    reset = resp.headers.get("X-RateLimit-Reset")
    if remaining == "0" and reset:
        try:
            wait = int(reset) - int(time.time()) + 1
            return min(max(wait, 0), _MAX_SLEEP_S)
        except ValueError:
            pass

    # Exponential backoff with jitter: 0.5 → 1 → 2 → 4 → 8, capped at 20s.
    backoff = min(_BASE_BACKOFF_S * (2 ** attempt), _MAX_BACKOFF_S)
    jitter = random.uniform(0, 0.25)
    return backoff + jitter


@dataclass
class GitHubClient:
    token: Optional[str] = None
    timeout_s: float = 20.0

    def _headers(self) -> dict[str, str]:
        h = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "RepoPulse/0.1",
        }
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def get_json(self, path: str, params: Optional[dict[str, Any]] = None) -> Any:
        url = f"{GITHUB_API}{path}"
        last_exc: Exception | None = None

        with httpx.Client(timeout=self.timeout_s, headers=self._headers()) as client:
            for attempt in range(_MAX_ATTEMPTS):
                try:
                    resp = client.get(url, params=params)
                except (httpx.TimeoutException, httpx.ConnectError) as exc:
                    last_exc = exc
                    wait = min(_BASE_BACKOFF_S * (2 ** attempt) + random.uniform(0, 0.25), _MAX_BACKOFF_S)
                    log.warning("GitHub request error (attempt %d/%d): %s — retrying in %.1fs", attempt + 1, _MAX_ATTEMPTS, exc, wait)
                    time.sleep(wait)
                    continue

                status = resp.status_code

                # Terminal: never retry these.
                if status in _NO_RETRY_STATUSES:
                    resp.raise_for_status()

                # 403: only retry when it looks like rate limiting.
                if status == 403:
                    if not _is_rate_limit_403(resp):
                        resp.raise_for_status()
                    wait = _sleep_seconds(resp, attempt)
                    log.warning("GitHub rate limit (403, attempt %d/%d) — sleeping %.1fs", attempt + 1, _MAX_ATTEMPTS, wait)
                    time.sleep(wait)
                    last_exc = httpx.HTTPStatusError(f"HTTP 403", request=resp.request, response=resp)
                    continue

                # 429 / 502 / 503 / 504: transient, always retry.
                if status in _RETRY_STATUSES:
                    wait = _sleep_seconds(resp, attempt)
                    log.warning("GitHub transient error %d (attempt %d/%d) — sleeping %.1fs", status, attempt + 1, _MAX_ATTEMPTS, wait)
                    time.sleep(wait)
                    last_exc = httpx.HTTPStatusError(f"HTTP {status}", request=resp.request, response=resp)
                    continue

                # Success or any other status: raise immediately.
                resp.raise_for_status()
                return resp.json()

        # All attempts exhausted.
        if last_exc is not None:
            raise last_exc
        raise RuntimeError(f"get_json failed after {_MAX_ATTEMPTS} attempts: {url}")
