from __future__ import annotations

from typing import Optional

from reinsight_sdk.models import TopExposuresResponse


class TopExposuresAPI:
    def __init__(self, client):
        self._client = client

    def top_exposures(
        self,
        portfolio_id: int,
        by: str = "tiv",
        limit: int = 50,
        country: Optional[str] = None,
        lob: Optional[str] = None,
        peril: Optional[str] = None,
    ) -> TopExposuresResponse:
        params = {
            "portfolio_id": portfolio_id,
            "by": by,
            "limit": limit,
        }
        if country:
            params["country"] = country
        if lob:
            params["lob"] = lob
        if peril:
            params["peril"] = peril

        resp = self._client._request("GET", "/v1/analytics/top-exposures", params=params)
        return TopExposuresResponse.model_validate(resp.json())