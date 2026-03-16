from __future__ import annotations

from reinsight_sdk.models import DataQualityResponse


class PortfoliosAPI:
    def __init__(self, client):
        self._client = client

    def data_quality(self, portfolio_id: int) -> DataQualityResponse:
        resp = self._client._request("GET", f"/v1/portfolios/{portfolio_id}/data-quality")
        return DataQualityResponse.model_validate(resp.json())