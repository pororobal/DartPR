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
    signal_horizon: Optional[str] = None
    cerebras_sentiment: Optional[str] = None
    cerebras_confidence: Optional[str] = None
    cerebras_reason: Optional[str] = None
    llm_summary: Optional[str] = None
    key_metrics: Optional[List[KeyMetricItem]] = None
    llm_status: str = "PENDING"
    created_at: Optional[datetime] = None
    # 관련공시 컨텍스트 연결
    related_status: str = "NONE"
    merged_summary: Optional[str] = None
    merged_sentiment: Optional[str] = None
    merged_horizon: Optional[str] = None
    merged_confidence: Optional[str] = None
    related_disclosures: Optional[List[dict]] = None
    # DVI 점수 근거 (서버에서 동적 생성)
    score_factors: List[str] = []


class DisclosureListResponse(BaseModel):
    data: List[DisclosureResponse]
    total: int
    page: int
    per_page: int
