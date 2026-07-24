"""Disclosure endpoints — live feed (auth+delay) + history (full filters)."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Header

from app.services.supabase_client import get_supabase
from app.schemas.disclosure import DisclosureResponse, DisclosureListResponse
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["disclosures"])

DART_BASE_URL = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo="


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


_SELECT_COLS = (
    "id,dart_rcept_no,ticker,company_name,title,published_at,"
    "category,sub_type,sub_rule_id,dvi_score,impact_level,risk_flag,"
    "is_feed_visible,deceptive_pattern_detected,momentum_authenticity,"
    "llm_summary,key_metrics,llm_status,created_at"
)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

async def _resolve_user_from_token(authorization: str = Header(None)) -> Optional[dict]:
    """If the request carries a valid Supabase JWT, return user info. Else None."""
    if not authorization:
        return None
    try:
        import jwt as pyjwt
        token = authorization.replace("Bearer ", "")
        payload = pyjwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"verify_aud": False},
        )
        return payload
    except Exception:
        return None


async def _resolve_user_from_api_key(x_api_key: str = Header(None)) -> Optional[dict]:
    """Check if request has a valid developer API key with Pro/Developer plan."""
    if not x_api_key:
        return None
    try:
        supabase = get_supabase()
        result = (
            supabase.table("users")
            .select("id, plan, api_key")
            .eq("api_key", x_api_key)
            .maybe_single()
            .execute()
        )
        if result.data and result.data.get("plan") in ("pro", "admin"):
            return result.data
    except Exception:
        pass
    return None


async def get_premium_user(
    authorization: str = Header(None),
    x_api_key: str = Header(None),
) -> Optional[dict]:
    """Combine JWT + API key checks. Returns user dict if premium, else None."""
    user = await _resolve_user_from_token(authorization)
    if user:
        return user
    user = await _resolve_user_from_api_key(x_api_key)
    if user:
        return user
    return None


# ---------------------------------------------------------------------------
# /live — Feed with 3-min delay for free users
# ---------------------------------------------------------------------------


@router.get("/live")
async def get_live_feed(
    limit: int = Query(20, ge=1, le=100),
    user: Optional[dict] = Depends(get_premium_user),
):
    """
    Real-time disclosure feed.

    - Premium (Pro/Developer) users: see all visible disclosures immediately.
    - Free / anonymous users: see disclosures published ≥ 3 minutes ago.
    """
    supabase = get_supabase()
    query = (
        supabase.table("disclosures")
        .select(_SELECT_COLS)
        .eq("is_feed_visible", True)
        .order("published_at", desc=True)
        .limit(limit)
    )

    # Free/anonymous: impose 3-min delay
    if not user:
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=settings.free_tier_delay_seconds)).isoformat()
        query = query.lte("published_at", cutoff)

    result = query.execute()
    data = [_row_to_response(r) for r in (result.data or [])]
    return {"data": data, "total": len(data)}


# ---------------------------------------------------------------------------
# /history — Full search with filters (public)
# ---------------------------------------------------------------------------


@router.get("/history")
async def get_history(
    ticker: Optional[str] = Query(None, description="종목코드 (부분일치)"),
    company_name: Optional[str] = Query(None, description="회사명 (부분일치)"),
    category: Optional[str] = Query(None, description="카테고리 (정확일치)"),
    score_min: Optional[int] = Query(None, ge=0, le=100, description="최소 DVI 점수"),
    score_max: Optional[int] = Query(None, ge=0, le=100, description="최대 DVI 점수"),
    date_from: Optional[str] = Query(None, description="시작일 (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="종료일 (YYYY-MM-DD)"),
    risk_flag: Optional[str] = Query(None, description="리스크 필터 (예: HIGH_RISK_TRAP)"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """
    Public search & filter endpoint for disclosure history.

    Supports: ticker, company_name, category, score range, date range, risk_flag.
    """
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


# ---------------------------------------------------------------------------
# /poll — Manual poll trigger
# ---------------------------------------------------------------------------


@router.post("/poll")
async def trigger_poll():
    """Manually trigger a DART poll cycle."""
    from app.services.dart_poller import poll_dart_once
    await poll_dart_once()
    return {"message": "Poll cycle triggered"}


# ---------------------------------------------------------------------------
# /reclassify — Re-run scoring on existing disclosures
# ---------------------------------------------------------------------------


@router.post("/reclassify")
async def reclassify_disclosures():
    """
    Re-run the full scoring pipeline on all existing disclosures.

    Updates: category, sub_type, sub_rule_id, dvi_score, impact_level,
    risk_flag, is_feed_visible, deceptive_pattern_detected, momentum_authenticity,
    llm_status (PENDING → DONE for low-score items).
    """
    from app.services.rules_engine import evaluate_disclosure

    supabase = get_supabase()
    result = (
        supabase.table("disclosures")
        .select("id,dart_rcept_no,title,raw_text,ticker")
        .execute()
    )
    rows = result.data or []
    updated = 0
    skipped = 0

    for row in rows:
        title = row.get("title", "")
        raw_text = row.get("raw_text", "")
        ticker = row.get("ticker", "")

        score_result = evaluate_disclosure(
            title=title, raw_text=raw_text, ticker=ticker, supabase=supabase,
        )

        supabase.table("disclosures").update({
            "category": score_result.category,
            "sub_type": score_result.sub_type,
            "sub_rule_id": score_result.sub_rule_id,
            "dvi_score": score_result.dvi_score,
            "impact_level": score_result.impact_level,
            "risk_flag": score_result.risk_flag,
            "is_feed_visible": score_result.is_feed_visible,
            "deceptive_pattern_detected": score_result.deceptive_pattern_detected,
            "momentum_authenticity": score_result.momentum_authenticity,
            "llm_status": "DONE" if score_result.skip_llm else "PENDING",
        }).eq("id", row["id"]).execute()
        updated += 1
        logger.debug(f"Reclassified {row['id']}: score={score_result.dvi_score}")

    return {"message": f"Re-classified {updated} disclosures"}


# ---------------------------------------------------------------------------
# /stats — Quick aggregate stats
# ---------------------------------------------------------------------------


@router.get("/stats")
async def get_stats():
    """Get aggregate stats about the disclosure database."""
    supabase = get_supabase()
    total = supabase.table("disclosures").select("id", count="exact").execute()
    visible = (
        supabase.table("disclosures")
        .select("id", count="exact")
        .eq("is_feed_visible", True)
        .execute()
    )
    category_counts = {}
    try:
        cat_result = supabase.table("disclosures").select("category").execute()
        for r in cat_result.data or []:
            c = r.get("category", "UNKNOWN")
            category_counts[c] = category_counts.get(c, 0) + 1
    except Exception:
        pass

    return {
        "total_disclosures": total.count if hasattr(total, "count") else 0,
        "feed_visible": visible.count if hasattr(visible, "count") else 0,
        "by_category": category_counts,
    }


# ---------------------------------------------------------------------------
# /{id}/analyze — Manual LLM trigger (admin only)
# ---------------------------------------------------------------------------


@router.post("/{disclosure_id}/analyze")
async def trigger_llm_analysis(
    disclosure_id: str,
    user: Optional[dict] = Depends(get_premium_user),
):
    """
    Manually trigger LLM analysis for a specific disclosure.

    Admin-only endpoint to re-run or trigger LLM enrichment.
    """
    if not user or user.get("plan") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    from app.services.groq_llm import analyze_disclosure

    supabase = get_supabase()
    
    # Get disclosure data
    result = (
        supabase.table("disclosures")
        .select("id,dart_rcept_no,ticker,company_name,title,raw_text,dvi_score")
        .eq("id", disclosure_id)
        .maybe_single()
        .execute()
    )
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Disclosure not found")
    
    row = result.data
    rcept_no = row.get("dart_rcept_no", "")
    ticker = row.get("ticker", "")
    corp_name = row.get("company_name", "")
    title = row.get("title", "")
    raw_text = row.get("raw_text", "")
    score = row.get("dvi_score", 0)
    
    # Determine brief vs full analysis
    brief = score < 80
    
    try:
        llm_result = await analyze_disclosure(
            ticker=ticker,
            company_name=corp_name,
            title=title,
            raw_text=raw_text,
            brief=brief,
        )
        
        # Update database
        update_data = {
            "llm_summary": llm_result.llm_summary[:8000],
            "key_metrics": [m.model_dump() for m in llm_result.key_metrics],
            "llm_raw_response": llm_result.model_dump(),
            "llm_status": "DONE",
        }
        
        supabase.table("disclosures").update(update_data).eq(
            "id", disclosure_id
        ).execute()
        
        logger.info(f"Manual LLM analysis triggered for {disclosure_id}")
        return {"message": "LLM analysis completed", "summary": llm_result.llm_summary[:200]}
        
    except Exception as e:
        logger.error(f"Manual LLM analysis failed for {disclosure_id}: {e}")
        raise HTTPException(status_code=500, detail=f"LLM analysis failed: {str(e)}")
