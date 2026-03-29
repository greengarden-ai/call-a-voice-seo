"""
DataForSEO HTTP client.

Wraps requests with:
- Basic auth (login / password)
- Automatic retry with exponential backoff on 429 / 5xx
- Response validation (raises on API-level errors)
- Convenience post() helper that all scripts share
"""

import time
import logging
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import config

logger = logging.getLogger(__name__)


class DataForSEOError(Exception):
    """Raised when the API returns a non-success status_code in the task result."""


class DataForSEOClient:
    def __init__(self):
        self.base_url = config.DATAFORSEO_BASE_URL
        self.auth = (config.DATAFORSEO_LOGIN, config.DATAFORSEO_PASSWORD)
        self.session = self._build_session()

    # ------------------------------------------------------------------
    # Session setup
    # ------------------------------------------------------------------

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        session.auth = self.auth
        session.headers.update({"Content-Type": "application/json"})

        retry = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        return session

    # ------------------------------------------------------------------
    # Core request
    # ------------------------------------------------------------------

    def post(self, endpoint: str, payload: list[dict]) -> list[dict]:
        """
        POST to endpoint and return the list of task results.

        Args:
            endpoint: Path after base URL, e.g. "dataforseo_labs/google/competitors_domain/live"
            payload: List of task dicts as required by the endpoint.

        Returns:
            List of result dicts from response["tasks"][*]["result"][*].

        Raises:
            DataForSEOError: API-level error (bad credentials, quota, etc.)
            requests.HTTPError: Transport-level HTTP error after retries exhausted.
        """
        url = f"{self.base_url}/{endpoint}"
        logger.debug("POST %s | tasks=%d", url, len(payload))

        response = self.session.post(url, json=payload, timeout=60)
        response.raise_for_status()

        body = response.json()
        self._check_status(body)

        results = []
        for task in body.get("tasks", []):
            task_status = task.get("status_code", 0)
            if task_status not in (20000, 20100):
                msg = task.get("status_message", "unknown task error")
                raise DataForSEOError(f"Task error {task_status}: {msg}")
            for result in task.get("result") or []:
                results.append(result)

        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _check_status(self, body: dict) -> None:
        status_code = body.get("status_code", 0)
        if status_code not in (20000, 20100):
            msg = body.get("status_message", "unknown error")
            raise DataForSEOError(f"API error {status_code}: {msg}")

    def paginated_post(
        self,
        endpoint: str,
        base_task: dict,
        total_limit: int,
        page_size: int = 100,
    ) -> list[dict]:
        """
        Repeatedly POST with offset/limit until total_limit items are fetched
        or the API returns fewer items than requested (last page).

        base_task must NOT include 'limit' or 'offset' — this method sets them.
        """
        all_items: list[dict] = []
        offset = 0

        while len(all_items) < total_limit:
            fetch = min(page_size, total_limit - len(all_items))
            task = {**base_task, "limit": fetch, "offset": offset}
            results = self.post(endpoint, [task])

            page_items = self._extract_items(results)
            all_items.extend(page_items)

            if len(page_items) < fetch:
                break  # last page

            offset += fetch
            time.sleep(0.5)  # be polite

        return all_items

    @staticmethod
    def _extract_items(results: list[dict]) -> list[dict]:
        """Pull the first 'items' list found in result dicts."""
        for result in results:
            items = result.get("items")
            if items:
                return items
        return []
