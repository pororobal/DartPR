"""Disclosure-related Pydantic schemas."""

from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class KeyMetricItem(BaseModel):
    label: str
    value: str
    status: str  # POSITIVE | NEUTRAL | NEGATIVE


class DisclosureResponse(BaseModel):
    id: str
    dart_rcept_no: str
    ticker: str
    company_name: str
    title: str
    published_at: datetime
    category: Optional[str] = None
    sub_rule_id: Optional[str] = None
    dvi_score: Optional[float] = None
    impact_level: Optional[str] = None
    risk_flag: Optional[str] = None
    deceptive_pattern_detected: Optional[bool] = None
    momentum_authenticity: Optional[str] = None
    llm_summary: Optional[str] = None
    key_metrics: Optional[List[KeyMetricItem]] = None
    llm_status: str = "PENDING"
    is_feed_visible: bool = False
    created_at: Optional[datetime] = None


class DisclosureListResponse(BaseModel):
    data: List[DisclosureResponse]
    total: int
    page: int
    per_page: int


class HistoryQueryParams(BaseModel):
    ticker: Optional[str] = None
    category: Optional[str] = None
    dvi_score_min: Optional[float] = None
    dvi_score_max: Optional[float] = None
    page: int = 1
    per_page: int = 20
