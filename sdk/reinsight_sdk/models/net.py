from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel


class TreatyModel(BaseModel):
    id: int
    name: str
    treaty_type: str
    ceded_share_pct: Optional[float] = None
    attachment: Optional[float] = None
    limit: Optional[float] = None


class NetTotals(BaseModel):
    gross_tiv: float
    ceded_tiv: float
    net_tiv: float
    ceded_pct: float


class NetBucket(BaseModel):
    key: str
    count: int
    gross_tiv: float
    ceded_tiv: float
    net_tiv: float
    ceded_pct: float


class NetResponse(BaseModel):
    portfolio_id: int
    treaty: TreatyModel
    count: int
    totals: NetTotals
    group_by: Optional[str] = None
    buckets: list[NetBucket] = []