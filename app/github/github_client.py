from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import time
import httpx

GITHUB_API = "https://api.github.com"

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
        with httpx.Client(timeout=self.timeout_s, headers=self._headers()) as client:
            resp = client.get(url, params=params)
            if resp.status_code == 403:
                # Handle secondary rate limits / primary rate limit
                reset = resp.headers.get("X-RateLimit-Reset")
                remaining = resp.headers.get("X-RateLimit-Remaining")
                if remaining == "0" and reset:
                    sleep_s = max(0, int(reset) - int(time.time())) + 1
                    time.sleep(min(sleep_s, 60))  # MVP cap
                    resp = client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()