from __future__ import annotations
from reinsight_sdk.models import HealthResponse

class HealthAPI:
    def __init__(self, client):
        self._client = client

    def get(self) -> HealthResponse:
        resp = self._client._request("GET", "/health/")
        return HealthResponse.model_validate(resp.json())