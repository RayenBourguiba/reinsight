from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class MappingSuggestion(BaseModel):
    field: str
    suggested_column: Optional[str] = None
    confidence: float
    required: bool


class SuggestMappingResponse(BaseModel):
    model_config = ConfigDict(extra="allow")  # tolerate extra keys if backend adds more later

    upload_id: str
    filename: str
    delimiter: str
    columns: list[str]

    canonical_required: list[str]
    canonical_optional: list[str]

    suggestions: list[MappingSuggestion]
    mapping: dict[str, str]

    missing_required_fields: list[str] = Field(default_factory=list)
    unmapped_columns: list[str] = Field(default_factory=list)

    notes: list[str] = Field(default_factory=list)


class ApplyMappingStats(BaseModel):
    max_rows: int
    preview_rows: int
    parsed_rows: int
    valid_rows: int
    invalid_rows: int
    error_rows_returned: int


class ApplyMappingNextStep(BaseModel):
    hint: str
    endpoint: str


class ApplyMappingRowError(BaseModel):
    row_number: int
    reason: str
    raw_row: Optional[dict[str, Any]] = None


class ApplyMappingResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    upload_id: str
    filename: str
    encoding: str
    delimiter: str

    stats: ApplyMappingStats
    mapping: dict[str, str]
    normalized_preview: list[dict[str, Any]] = Field(default_factory=list)
    row_errors: list[ApplyMappingRowError] = Field(default_factory=list)
    next_step: ApplyMappingNextStep

    # Only present if include_rows=true
    normalized_rows: Optional[list[dict[str, Any]]] = None