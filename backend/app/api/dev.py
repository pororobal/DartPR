"""Developer API endpoints — API key authentication for auto-trading bots."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Query
from app.services.supabase_client import get_supabase
from app.schemas.disclosure import DisclosureListResponse
from app.config import settings

router = APIRouter(tags=["developer"])


async def verify_api_key(x_api_key: str = Header(...)):
    """
    Verify the X-API-Key header against the users table.
    Returns user dict with plan info.
    """
    supabase = get_supabase()
    result = (
        supabase.table("users")
        .select("*")
        .eq("api_key", x_api_key)
        .maybe_single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid API key")

    user = result.data
    if user.get("plan") != "developer":
        raise HTTPException(
            status_code=403,
            detail="API key valid but plan is not 'developer'",
        )

    return user


def _row_to_response(row: dict) -> dict:
    return {
        "id": row.get("id", ""),
        "dart_rcept_no": row.get("dart_rcept_no", ""),
        "ticker": row.get("ticker", ""),
        "company_name": row.get("company_name", ""),
        "title": row.get("title", ""),
        "published_at": row.get("published_at", ""),
        "category": row.get("category"),
        "sub_rule_id": row.get("sub_rule_id"),
        "dvi_score": row.get("dvi_score"),
        "impact_level": row.get("impact_level"),
        "risk_flag": row.get("risk_flag"),
        "deceptive_pattern_detected": row.get("deceptive_pattern_detected"),
        "momentum_authenticity": row.get("momentum_authenticity"),
        "llm_summary": row.get("llm_summary"),
        "key_metrics": row.get("key_metrics"),
        "llm_status": row.get("llm_status", "PENDING"),
        "is_feed_visible": row.get("is_feed_visible", False),
        "created_at": row.get("created_at"),
    }


@router.get("/disclosures/live")
async def dev_live_feed(user: dict = Depends(verify_api_key)):
    """
    Real-time disclosure feed for developer API.
    No delay, all feed-visible disclosures.
    Rate limit: 100 req/min per API key (TODO: implement middleware).
    """
    supabase = get_supabase()
    result = (
        supabase.table("disclosures")
        .select("*")
        .eq("is_feed_visible", True)
        .order("published_at", desc=True)
        .limit(50)
        .execute()
    )

    data = [_row_to_response(r) for r in (result.data or [])]
    return {
        "data": data,
        "total": len(data),
        "page": 1,
        "per_page": 50,
    }


@router.get("/disclosures/history")
async def dev_history(
    ticker: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    dvi_score_min: Optional[float] = Query(None),
    dvi_score_max: Optional[float] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: dict = Depends(verify_api_key),
):
    """
    Full disclosure history for developer API.
    No delay, all results, full filtering.
    """
    supabase = get_supabase()
    query = supabase.table("disclosures").select("*", count="exact")

    if ticker:
        query = query.ilike("ticker", f"%{ticker}%")
    if category:
        query = query.eq("category", category)
    if dvi_score_min is not None:
        query = query.gte("dvi_score", dvi_score_min)
    if dvi_score_max is not None:
        query = query.lte("dvi_score", dvi_score_max)

    offset = (page - 1) * per_page
    result = query.order("published_at", desc=True).range(
        offset, offset + per_page - 1
    ).execute()

    data = [_row_to_response(r) for r in (result.data or [])]
    total = result.count if hasattr(result, "count") else len(data)

    return {
        "data": data,
        "total": total,
        "page": page,
        "per_page": per_page,
    }
