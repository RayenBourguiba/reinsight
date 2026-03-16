from __future__ import annotations

from pathlib import Path
from typing import Union, Optional, Any

from reinsight_sdk.models import (
    UploadResponse,
    UploadPreviewResponse,
    SuggestMappingResponse,
    ApplyMappingResponse,
)
from reinsight_sdk.models import IngestCsvResult

class IngestionAPI:
    def __init__(self, client):
        self._client = client

    def upload_csv(
        self,
        portfolio_id: int,
        file_path: Union[str, Path],
        *,
        field_name: str = "file",
    ) -> UploadResponse:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        url = "/v1/ingestion/uploads"

        with path.open("rb") as f:
            files = {field_name: (path.name, f, "text/csv")}
            data = {"portfolio_id": str(portfolio_id)}  # backend ignores for now, ok

            resp = self._client._http.request(
                "POST",
                url,
                files=files,
                data=data,
            )

        self._client._raise_for_status(resp)
        return UploadResponse.model_validate(resp.json())

    def get_upload(self, upload_id: str) -> UploadResponse:
        resp = self._client._request("GET", f"/v1/ingestion/uploads/{upload_id}")
        return UploadResponse.model_validate(resp.json())

    # optional alias (keep one)
    def get_status(self, upload_id: str) -> UploadResponse:
        return self.get_upload(upload_id)

    def preview(self, upload_id: str, rows: int = 50) -> UploadPreviewResponse:
        resp = self._client._request(
            "GET",
            f"/v1/ingestion/uploads/{upload_id}/preview",
            params={"rows": rows},
        )
        return UploadPreviewResponse.model_validate(resp.json())

    def suggest_mapping(self, upload_id: str) -> SuggestMappingResponse:
        resp = self._client._request(
            "POST",
            f"/v1/ingestion/uploads/{upload_id}/suggest-mapping",
        )
        return SuggestMappingResponse.model_validate(resp.json())

    def apply_mapping(
        self,
        upload_id: str,
        *,
        mapping: dict[str, str],
        options: Optional[dict[str, Any]] = None,
        transforms: Optional[dict[str, Any]] = None,
    ) -> ApplyMappingResponse:
        payload: dict[str, Any] = {"mapping": mapping}
        if options is not None:
            payload["options"] = options
        if transforms is not None:
            payload["transforms"] = transforms

        resp = self._client._request(
            "POST",
            f"/v1/ingestion/uploads/{upload_id}/apply-mapping",
            json=payload,
        )
        return ApplyMappingResponse.model_validate(resp.json())

    def ingest_csv(
        self,
        *,
        portfolio_id: int,
        file_path: str,
        dedup_mode: str = "composite",
        batch_size: int = 1000,
        max_errors: int = 200,
        max_rows: int = 5000,
        preview_rows: int = 20,
    ) -> IngestCsvResult:
        """
        High-level helper:
        upload -> suggest mapping -> apply mapping -> bulk create exposures
        """
        upload = self.upload_csv(portfolio_id=portfolio_id, file_path=file_path)

        suggested = self.suggest_mapping(upload.upload_id)

        applied = self.apply_mapping(
            upload.upload_id,
            mapping=suggested.mapping,
            options={
                "max_rows": max_rows,
                "preview_rows": preview_rows,
                "include_rows": True,
            },
        )

        rows = applied.normalized_rows or []

        bulk = self._client.exposures.bulk_create(
            portfolio_id=portfolio_id,
            rows=rows,
            batch_size=batch_size,
            max_errors=max_errors,
            dedup_mode=dedup_mode,
        )

        return IngestCsvResult(
            upload=upload,
            suggested_mapping=suggested,
            applied_mapping=applied,
            bulk_result=bulk,
        )