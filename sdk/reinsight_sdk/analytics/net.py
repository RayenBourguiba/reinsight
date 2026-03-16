from __future__ import annotations

from typing import Optional

from reinsight_sdk.models import NetResponse


class NetAPI:
    def __init__(self, client):
        self._client = client

    def net_of_treaty(
        self,
        portfolio_id: int,
        treaty_id: int,
        group_by: Optional[str] = None,
        lob: Optional[str] = None,
        peril: Optional[str] = None,
        country: Optional[str] = None,
        region: Optional[str] = None,
    ) -> NetResponse:
        params = {
            "portfolio_id": portfolio_id,
            "treaty_id": treaty_id,
        }
        if group_by:
            params["group_by"] = group_by
        if lob:
            params["lob"] = lob
        if peril:
            params["peril"] = peril
        if country:
            params["country"] = country
        if region:
            params["region"] = region

        resp = self._client._request("GET", "/v1/analytics/net", params=params)
        return NetResponse.model_validate(resp.json())