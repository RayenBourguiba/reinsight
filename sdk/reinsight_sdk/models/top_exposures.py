from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


class ExposureItem(BaseModel):
    id: int
    policy_id: str = ""
    location_id: str = ""
    lob: str
    peril: str
    country: str
    region: str = ""
    tiv: float
    premium: Optional[float] = None


class TopExposuresFilters(BaseModel):
    country: Optional[str] = None
    lob: Optional[str] = None
    peril: Optional[str] = None


class TopExposuresResponse(BaseModel):
    portfolio_id: int
    by: str
    limit: int
    filters: TopExposuresFilters
    count: int
    items: list[ExposureItem]