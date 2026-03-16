from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class BulkCreateExposuresResponse(BaseModel):
    portfolio_id: int
    dedup_mode: str = "none"
    received_rows: int
    inserted_rows: int
    skipped_duplicates: int = 0
    error_rows: int = 0
    errors: list[dict[str, Any]] = Field(default_factory=list)
    notes: Optional[list[str]] = None