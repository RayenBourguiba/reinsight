from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class ScenarioFilters(BaseModel):
    country: Optional[str] = None
    lob: Optional[str] = None
    peril: Optional[str] = None
    region: Optional[str] = None


class ScenarioStress(BaseModel):
    name: str
    filters: ScenarioFilters = Field(default_factory=ScenarioFilters)
    tiv_factor: float = Field(..., gt=0)


class ScenarioTotals(BaseModel):
    count: int
    gross_tiv: float
    ceded_tiv: float
    net_tiv: float
    ceded_pct: float


class ScenarioDelta(BaseModel):
    gross_tiv: float
    gross_tiv_pct: float
    net_tiv: float
    net_tiv_pct: float


class ScenarioBucket(BaseModel):
    key: str
    count: int
    gross_tiv: float
    ceded_tiv: float
    net_tiv: float


class ScenarioBuckets(BaseModel):
    baseline: list[ScenarioBucket] = Field(default_factory=list)
    stressed: list[ScenarioBucket] = Field(default_factory=list)


class TreatyInfo(BaseModel):
    id: int
    name: str
    treaty_type: str
    ceded_share_pct: Optional[float] = None
    attachment: Optional[float] = None
    limit: Optional[float] = None


class ScenarioRequest(BaseModel):
    portfolio_id: int
    treaty_id: Optional[int] = None
    base_filters: ScenarioFilters = Field(default_factory=ScenarioFilters)
    stresses: list[ScenarioStress]
    group_by: Optional[str] = None


class ScenarioResponse(BaseModel):
    portfolio_id: int
    treaty: Optional[TreatyInfo] = None
    base_filters: dict[str, Any] = Field(default_factory=dict)
    stresses: list[dict[str, Any]] = Field(default_factory=list)
    group_by: Optional[str] = None
    baseline: ScenarioTotals
    stressed: ScenarioTotals
    delta: ScenarioDelta
    buckets: Optional[ScenarioBuckets] = None