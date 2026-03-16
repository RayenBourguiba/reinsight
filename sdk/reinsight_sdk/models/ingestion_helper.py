from __future__ import annotations

from pydantic import BaseModel

from reinsight_sdk.models import (
    UploadResponse,
    SuggestMappingResponse,
    ApplyMappingResponse,
    BulkCreateExposuresResponse,
)


class IngestCsvResult(BaseModel):
    upload: UploadResponse
    suggested_mapping: SuggestMappingResponse
    applied_mapping: ApplyMappingResponse
    bulk_result: BulkCreateExposuresResponse