"""HTTP client for the CRM API: auth, pagination, retries with exponential backoff."""
import logging
import time

import requests

log = logging.getLogger(__name__)
RETRYABLE = {429, 500, 502, 503, 504}


class CrmClient:
    def __init__(self, base_url: str, token: str, page_size: int = 1000, max_retries: int = 6, timeout: int = 60):
        self.base_url = base_url.rstrip("/")
        self.page_size = page_size
        self.max_retries = max_retries
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}", "Accept": "application/json"})

    def _get(self, path: str, params: dict) -> dict:
        for attempt in range(self.max_retries + 1):
            try:
                r = self.session.get(f"{self.base_url}{path}", params=params, timeout=self.timeout)
            except requests.RequestException as exc:
                if attempt == self.max_retries:
                    raise
                wait = 2 ** attempt
                log.warning("Network error on %s (%s); retrying in %ss", path, exc, wait)
                time.sleep(wait)
                continue
            if r.status_code in RETRYABLE and attempt < self.max_retries:
                wait = float(r.headers.get("Retry-After", 2 ** attempt))
                log.warning("HTTP %s on %s; retrying in %ss", r.status_code, path, wait)
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        raise RuntimeError("unreachable")

    def paginate(self, path: str, updated_since: str | None = None):
        """Yield pages of records until the API stops returning a cursor."""
        params = {"limit": self.page_size}
        if updated_since:
            params["updated_since"] = updated_since
        cursor = None
        while True:
            if cursor is not None:
                params["cursor"] = cursor
            body = self._get(path, params)
            yield body.get("data", [])
            cursor = body.get("next_cursor")
            if cursor is None:
                return

    def get_report(self, path: str, **params) -> list[dict]:
        return self._get(path, params).get("data", [])
