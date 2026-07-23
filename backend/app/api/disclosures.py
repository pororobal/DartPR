"""Disclosure endpoints — live feed, history, delayed feed."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from app.services.supabase_client import get_supabase
from app.schemas.disclosure import DisclosureResponse, DisclosureListResponse
from app.api.auth import get_current_user, optional_get_current_user, require_plan
from app.config import settings

router = APIRouter(tags=["disclosures"])


def _row_to_response(row: dict) -> dict:
    """Convert a Supabase row dict to a serializable response dict."""
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


# ---------------------------------------------------------------------------
# Public: delayed feed (Free tier — 3 min delay)
# ---------------------------------------------------------------------------

@router.get("/delayed")
async def get_delayed_feed():
    """
    Public endpoint — no auth required.
    Returns feed-visible disclosures published > free_tier_delay_seconds ago.
    """
    supabase = get_supabase()
    cutoff = datetime.now(timezone.utc) - timedelta(
        seconds=settings.free_tier_delay_seconds
    )

    result = (
        supabase.table("disclosures")
        .select("*")
        .eq("is_feed_visible", True)
        .lt("published_at", cutoff.isoformat())
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


# ---------------------------------------------------------------------------
# Authenticated: live feed (Pro/Developer — no delay)
# ---------------------------------------------------------------------------

@router.get("/live")
async def get_live_feed(user: dict = Depends(require_plan("pro"))):
    """
    Requires Pro or Developer plan.
    Returns feed-visible disclosures with NO delay.
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


# ---------------------------------------------------------------------------
# History (search + filter + pagination)
# ---------------------------------------------------------------------------

@router.get("/history")
async def get_history(
    ticker: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    dvi_score_min: Optional[float] = Query(None),
    dvi_score_max: Optional[float] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: Optional[dict] = Depends(optional_get_current_user),
):
    """
    Search disclosure history with filters.
    Free users see 3-min delayed data; Pro/Dev users see all.
    """
    supabase = get_supabase()
    query = supabase.table("disclosures").select("*", count="exact")

    # Apply filters
    if ticker:
        query = query.ilike("ticker", f"%{ticker}%")
    if category:
        query = query.eq("category", category)
    if dvi_score_min is not None:
        query = query.gte("dvi_score", dvi_score_min)
    if dvi_score_max is not None:
        query = query.lte("dvi_score", dvi_score_max)

    # Free tier delay
    if not user or user.get("plan", "free") == "free":
        cutoff = datetime.now(timezone.utc) - timedelta(
            seconds=settings.free_tier_delay_seconds
        )
        query = query.lt("published_at", cutoff.isoformat())

    # Pagination
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


# ---------------------------------------------------------------------------
# Manual poll trigger (admin/pro only)
# ---------------------------------------------------------------------------

@router.post("/poll")
async def trigger_poll(user: dict = Depends(require_plan("pro"))):
    """Manually trigger a DART poll cycle."""
    from app.services.dart_poller import poll_dart_once
    await poll_dart_once()
    return {"message": "Poll cycle triggered"}


# ---------------------------------------------------------------------------
# Re-classify existing disclosures (fix BIOTECH over-classification)
# ---------------------------------------------------------------------------

@router.post("/reclassify")
async def reclassify_disclosures(user: dict = Depends(require_plan("pro"))):
    """
    Re-run _guess_category + compute_score on all existing disclosures
    that still have the old BIOTECH/bio_ind_approval classification.
    Fixes data inserted before the keyword-priority fix.
    """
    from app.services.dart_poller import _guess_category
    from app.services.rules_engine import compute_score

    supabase = get_supabase()
    result = (
        supabase.table("disclosures")
        .select("id,dart_rcept_no,title,raw_text,category,sub_rule_id")
        .execute()
    )
    rows = result.data or []
    updated = 0

    for row in rows:
        title = row.get("title", "")
        raw_text = row.get("raw_text", "")
        old_cat = row.get("category")
        new_cat, sub_rule_flags = _guess_category(title, raw_text)

        if old_cat == new_cat and row.get("sub_rule_id") != "bio_ind_approval":
            continue  # skip if unchanged and not the old default sub-rule

        score_result = compute_score(new_cat, sub_rule_flags)
        supabase.table("disclosures").update({
            "category": new_cat,
            "sub_rule_id": score_result.sub_rule_id,
            "dvi_score": score_result.dvi_score,
            "impact_level": score_result.impact_level,
            "risk_flag": score_result.risk_flag,
            "is_feed_visible": score_result.is_feed_visible or score_result.risk_flag == "HIGH_RISK_TRAP",
        }).eq("id", row["id"]).execute()
        updated += 1

    return {"message": f"Re-classified {updated} disclosures"}
