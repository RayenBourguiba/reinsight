from __future__ import annotations

from typing import Optional, Any
from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    upload_id: str = Field(..., description="Upload UUID")
    status: str
    filename: Optional[str] = None
    created_at: Optional[str] = None

    portfolio_id: Optional[int] = None
    message: Optional[str] = None

class UploadPreviewResponse(BaseModel):
    upload_id: str
    filename: str
    encoding: str
    delimiter: str
    columns: list[str]
    preview_rows: list[dict[str, Any]]
    returned_rows: int