from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class DataQualityTotals(BaseModel):
    exposures: int


class MissingRequiredCounts(BaseModel):
    lob: int
    peril: int
    country: int
    tiv: int


class MissingRequiredPct(BaseModel):
    lob: float
    peril: float
    country: float
    tiv: float


class MissingRequired(BaseModel):
    counts: MissingRequiredCounts
    pct: MissingRequiredPct


class InvalidValues(BaseModel):
    tiv_non_positive: int
    premium_negative: int


class DuplicatePolicyIdTop(BaseModel):
    policy_id: str
    count: int


class CompositeKey(BaseModel):
    policy_id: str
    country: str
    region: str
    lob: str
    peril: str


class DuplicateCompositeTop(BaseModel):
    key: CompositeKey
    count: int


class Duplicates(BaseModel):
    empty_policy_id: int
    by_policy_id_top: list[DuplicatePolicyIdTop] = Field(default_factory=list)
    by_composite_top: list[DuplicateCompositeTop] = Field(default_factory=list)


class OutlierExposure(BaseModel):
    id: int
    policy_id: str = ""
    country: str
    region: str = ""
    lob: str
    peril: str
    tiv: float


class Outliers(BaseModel):
    tiv_p95: float
    tiv_p99: float
    top_tiv: list[OutlierExposure] = Field(default_factory=list)


class DistBucket(BaseModel):
    key: str
    count: int
    tiv: float


class Distributions(BaseModel):
    by_country: list[DistBucket] = Field(default_factory=list)
    by_lob: list[DistBucket] = Field(default_factory=list)
    by_peril: list[DistBucket] = Field(default_factory=list)


class DataQualityResponse(BaseModel):
    portfolio_id: int
    totals: DataQualityTotals
    missing_required: MissingRequired
    invalid_values: InvalidValues
    duplicates: Duplicates
    outliers: Outliers
    distributions: Distributions
    notes: list[str] = Field(default_factory=list)