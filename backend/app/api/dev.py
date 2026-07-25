"""Developer API endpoints -- full access via API key."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query

from app.services.supabase_client import get_supabase
from app.schemas.disclosure import DisclosureListResponse
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["developer"])

DART_BASE_URL = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo="

_SELECT_COLS = (
    "id,dart_rcept_no,ticker,company_name,title,published_at,"
    "category,sub_type,sub_rule_id,dvi_score,impact_level,risk_flag,"
    "is_feed_visible,deceptive_pattern_detected,momentum_authenticity,"
    "llm_summary,key_metrics,llm_status,created_at"
)


async def verify_api_key(x_api_key: str = Header(...)):
    supabase = get_supabase()
    result = (
        supabase.table("users")
        .select("id, plan")
        .eq("api_key", x_api_key)
        .maybe_single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid API key")

    user = result.data
    if user.get("plan") not in ("pro", "developer"):
        raise HTTPException(
            status_code=403,
            detail="API key valid but plan is not 'pro' or 'developer'",
        )

    return user


def _row_to_response(row: dict) -> dict:
    rcept_no = row.get("dart_rcept_no", "")
    return {
        "id": row.get("id", ""),
        "dart_rcept_no": rcept_no,
        "dart_url": f"{DART_BASE_URL}{rcept_no}",
        "ticker": row.get("ticker", ""),
        "company_name": row.get("company_name", ""),
        "title": row.get("title", ""),
        "published_at": row.get("published_at", ""),
        "category": row.get("category"),
        "sub_type": row.get("sub_type"),
        "sub_rule_id": row.get("sub_rule_id"),
        "dvi_score": row.get("dvi_score"),
        "impact_level": row.get("impact_level"),
        "risk_flag": row.get("risk_flag"),
        "is_feed_visible": row.get("is_feed_visible"),
        "deceptive_pattern_detected": row.get("deceptive_pattern_detected"),
        "momentum_authenticity": row.get("momentum_authenticity"),
        "llm_summary": row.get("llm_summary"),
        "key_metrics": row.get("key_metrics"),
        "llm_status": row.get("llm_status", "PENDING"),
        "created_at": row.get("created_at"),
    }


@router.get("/disclosures/live")
async def dev_live(
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(verify_api_key),
):
    """Developer live feed -- no delay (premium)."""
    supabase = get_supabase()
    result = (
        supabase.table("disclosures")
        .select(_SELECT_COLS)
        .eq("is_feed_visible", True)
        .order("published_at", desc=True)
        .limit(limit)
        .execute()
    )
    data = [_row_to_response(r) for r in (result.data or [])]
    return {"data": data, "total": len(data)}


@router.get("/disclosures/history")
async def dev_history(
    ticker: Optional[str] = Query(None),
    company_name: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    score_min: Optional[int] = Query(None, ge=0, le=100),
    score_max: Optional[int] = Query(None, ge=0, le=100),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    risk_flag: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: dict = Depends(verify_api_key),
):
    supabase = get_supabase()
    query = supabase.table("disclosures").select(_SELECT_COLS, count="exact")

    if ticker:
        query = query.ilike("ticker", f"%{ticker}%")
    if company_name:
        query = query.ilike("company_name", f"%{company_name}%")
    if category:
        query = query.eq("category", category)
    if score_min is not None:
        query = query.gte("dvi_score", score_min)
    if score_max is not None:
        query = query.lte("dvi_score", score_max)
    if date_from:
        query = query.gte("published_at", f"{date_from}T00:00:00")
    if date_to:
        query = query.lte("published_at", f"{date_to}T23:59:59")
    if risk_flag:
        query = query.eq("risk_flag", risk_flag)

    offset = (page - 1) * per_page
    result = (
        query.order("published_at", desc=True)
        .range(offset, offset + per_page - 1)
        .execute()
    )

    data = [_row_to_response(r) for r in (result.data or [])]
    total = result.count if hasattr(result, "count") else len(data)

    return DisclosureListResponse(
        data=data,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/disclosures/stats")
async def dev_stats(user: dict = Depends(verify_api_key)):
    supabase = get_supabase()
    total = supabase.table("disclosures").select("id", count="exact").execute()
    visible = (
        supabase.table("disclosures")
        .select("id", count="exact")
        .eq("is_feed_visible", True)
        .execute()
    )
    return {
        "total_disclosures": total.count if hasattr(total, "count") else 0,
        "feed_visible": visible.count if hasattr(visible, "count") else 0,
    }
