from __future__ import annotations

from reinsight_sdk.models import ScenarioRequest, ScenarioResponse


class ScenarioAPI:
    def __init__(self, client):
        self._client = client

    def scenario(self, payload: ScenarioRequest) -> ScenarioResponse:
        resp = self._client._request("POST", "/v1/analytics/scenario", json=payload.model_dump())
        return ScenarioResponse.model_validate(resp.json())