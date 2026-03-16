from pydantic import BaseModel, Field
from typing import Any


class AccumulationTotals(BaseModel):
    count: int
    total_tiv: float


class AccumulationBucket(BaseModel):
    key: str
    count: int
    tiv: float
    share_pct: float = Field(..., description="Percentage share of total_tiv")


class AccumulationResponse(BaseModel):
    portfolio_id: int
    group_by: str
    filters: dict[str, Any] = Field(default_factory=dict)
    totals: AccumulationTotals
    buckets: list[AccumulationBucket]