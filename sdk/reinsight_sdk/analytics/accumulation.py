from __future__ import annotations

from typing import Optional

from reinsight_sdk.models import AccumulationResponse


class AccumulationAPI:
    def __init__(self, client):
        self._client = client

    def accumulation(
        self,
        portfolio_id: int,
        group_by: str = "country",
        lob: Optional[str] = None,
        peril: Optional[str] = None,
        country: Optional[str] = None,
        region: Optional[str] = None,
        top_n: int = 10,
    ) -> AccumulationResponse:
        params = {
            "portfolio_id": portfolio_id,
            "group_by": group_by,
            "top_n": top_n,
        }
        if lob:
            params["lob"] = lob
        if peril:
            params["peril"] = peril
        if country:
            params["country"] = country
        if region:
            params["region"] = region

        resp = self._client._request("GET", "/v1/analytics/accumulation", params=params)
        return AccumulationResponse.model_validate(resp.json())