from __future__ import annotations

from typing import Any, Optional

from reinsight_sdk.models import BulkCreateExposuresResponse


class ExposuresAPI:
    def __init__(self, client):
        self._client = client

    def bulk_create(
        self,
        *,
        portfolio_id: int,
        rows: list[dict[str, Any]],
        batch_size: int = 1000,
        max_errors: int = 200,
        dedup_mode: str = "none",
    ) -> BulkCreateExposuresResponse:
        payload = {
            "portfolio_id": portfolio_id,
            "rows": rows,
            "batch_size": batch_size,
            "max_errors": max_errors,
            "dedup_mode": dedup_mode,
        }
        resp = self._client._request("POST", "/v1/exposures/bulk", json=payload)
        return BulkCreateExposuresResponse.model_validate(resp.json())