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
    dart_url: str
    ticker: str
    company_name: str
    title: str
    published_at: datetime
    category: Optional[str] = None
    sub_rule_id: Optional[str] = None
    sub_type: Optional[str] = None
    dvi_score: Optional[int] = None
    impact_level: Optional[str] = None
    risk_flag: Optional[str] = None
    is_feed_visible: Optional[bool] = None
    deceptive_pattern_detected: Optional[bool] = None
    momentum_authenticity: Optional[str] = None
    llm_summary: Optional[str] = None
    key_metrics: Optional[List[KeyMetricItem]] = None
    llm_status: str = "PENDING"
    created_at: Optional[datetime] = None


class DisclosureListResponse(BaseModel):
    data: List[DisclosureResponse]
    total: int
    page: int
    per_page: int
