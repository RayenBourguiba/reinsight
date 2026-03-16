from __future__ import annotations

import time
import httpx

from typing import Any, Optional

from reinsight_sdk.exceptions import (
    AuthError,
    ValidationError,
    RateLimitError,
    ServerError,
    NetworkError,
)
from reinsight_sdk.analytics.top_exposures import TopExposuresAPI
from reinsight_sdk.analytics.scenario import ScenarioAPI
from reinsight_sdk.portfolios.data_quality import PortfoliosAPI
from reinsight_sdk.analytics.accumulation import AccumulationAPI
from reinsight_sdk.analytics.net import NetAPI
from reinsight_sdk.health.health import HealthAPI
from reinsight_sdk.ingestion.uploads import IngestionAPI
from reinsight_sdk.exposures.exposures import ExposuresAPI

class Client:
    """
    Reinsight SDK client.

    Auth:
      - API key in header: X-API-Key
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 10.0,
        retries: int = 2,
        backoff: float = 0.4,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff

        self._http = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            headers={"X-API-Key": self.api_key},
        )

        # Sub-clients
        class _Analytics:
            def __init__(self, client):
                self.accumulation = AccumulationAPI(client).accumulation
                self.net_of_treaty = NetAPI(client).net_of_treaty
                self.top_exposures = TopExposuresAPI(client).top_exposures
                self.scenario = ScenarioAPI(client).scenario

        self.analytics = _Analytics(self)
        self.health = HealthAPI(self)
        self.portfolios = PortfoliosAPI(self)
        self.ingestion = IngestionAPI(self)
        self.exposures = ExposuresAPI(self)

    def close(self):
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def _request(self, method: str, path: str, params: Optional[dict[str, Any]] = None, json: Any = None):
        url = path if path.startswith("/") else f"/{path}"

        last_exc: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                resp = self._http.request(method, url, params=params, json=json)
                self._raise_for_status(resp)
                return resp
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_exc = e
                if attempt >= self.retries:
                    raise NetworkError(f"Network error after {attempt+1} attempts: {e}") from e
            except RateLimitError as e:
                last_exc = e
                if attempt >= self.retries:
                    raise
            except ServerError as e:
                last_exc = e
                if attempt >= self.retries:
                    raise

            # backoff before retry
            time.sleep(self.backoff * (2 ** attempt))

        # Should never reach here
        raise NetworkError(f"Request failed: {last_exc}")

    @staticmethod
    def _extract_error(resp: httpx.Response):
        """
        Tries to normalize API error payloads into:
          - message (str)
          - code (str|None)
          - details (any)
        """
        try:
            data = resp.json()
        except Exception:
            return (resp.text or "Request failed", None, None)

        # Our backend style: {"error": {"code": "...", "message": "...", "details": {...}}}
        if isinstance(data, dict) and "error" in data and isinstance(data["error"], dict):
            err = data["error"]
            return (
                err.get("message") or "Request failed",
                err.get("code"),
                err.get("details"),
            )

        # DRF default style sometimes: {"detail": "..."}
        if isinstance(data, dict) and "detail" in data:
            return (str(data["detail"]), None, None)

        # Fallback to whole json
        return (str(data), None, None)

    @staticmethod
    def _raise_for_status(resp: httpx.Response):
        status = resp.status_code
        if 200 <= status < 300:
            return

        message, code, details = Client._extract_error(resp)

        if status in (401, 403):
            raise AuthError(message, status_code=status, code=code, details=details)
        if status == 429:
            raise RateLimitError(message, status_code=status, code=code, details=details)
        if 400 <= status < 500:
            raise ValidationError(message, status_code=status, code=code, details=details)
        if 500 <= status < 600:
            raise ServerError(message, status_code=status, code=code, details=details)

        raise ValidationError(message, status_code=status, code=code, details=details)