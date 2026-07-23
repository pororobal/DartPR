"""Disclosure endpoints -- public feed, history, reclassify."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.services.supabase_client import get_supabase
from app.schemas.disclosure import DisclosureResponse, DisclosureListResponse
from app.config import settings

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
        "sub_rule_id": row.get("sub_rule_id"),
        "deceptive_pattern_detected": row.get("deceptive_pattern_detected"),
        "momentum_authenticity": row.get("momentum_authenticity"),
        "llm_summary": row.get("llm_summary"),
        "key_metrics": row.get("key_metrics"),
        "llm_status": row.get("llm_status", "PENDING"),
        "created_at": row.get("created_at"),
    }


# ---------------------------------------------------------------------------
# Public: disclosure list (all, ordered by published_at desc)
# ---------------------------------------------------------------------------

@router.get("/list")
async def get_disclosure_list():
    """
    Public endpoint -- no auth required.
    Returns all disclosures ordered by published_at desc.
    """
    supabase = get_supabase()
    result = (
        supabase.table("disclosures")
        .select("*")
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
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """
    Public endpoint -- no auth required.
    Search disclosure history with optional ticker/category filters.
    """
    supabase = get_supabase()
    query = supabase.table("disclosures").select("*", count="exact")

    if ticker:
        query = query.ilike("ticker", f"%{ticker}%")
    if category:
        query = query.eq("category", category)

    offset = (page - 1) * per_page
    result = (
        query.order("published_at", desc=True)
        .range(offset, offset + per_page - 1)
        .execute()
    )

    data = [_row_to_response(r) for r in (result.data or [])]
    total = result.count if hasattr(result, "count") else len(data)

    return {
        "data": data,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ---------------------------------------------------------------------------
# Manual poll trigger
# ---------------------------------------------------------------------------

@router.post("/poll")
async def trigger_poll():
    """Manually trigger a DART poll cycle."""
    from app.services.dart_poller import poll_dart_once

    await poll_dart_once()
    return {"message": "Poll cycle triggered"}


# ---------------------------------------------------------------------------
# Re-classify existing disclosures
# ---------------------------------------------------------------------------

@router.post("/reclassify")
async def reclassify_disclosures():
    """
    Re-run _guess_category on all existing disclosures using latest keyword logic.
    """
    from app.services.dart_poller import _guess_category

    supabase = get_supabase()
    result = (
        supabase.table("disclosures")
        .select("id,dart_rcept_no,title,raw_text,category")
        .execute()
    )
    rows = result.data or []
    updated = 0

    for row in rows:
        title = row.get("title", "")
        raw_text = row.get("raw_text", "")
        new_cat, _ = _guess_category(title, raw_text)

        if row.get("category") == new_cat:
            continue

        supabase.table("disclosures").update({
            "category": new_cat,
        }).eq("id", row["id"]).execute()
        updated += 1

    return {"message": f"Re-classified {updated} disclosures"}
