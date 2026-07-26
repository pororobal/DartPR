"""Disclosure endpoints — live feed (auth+delay) + history (full filters)."""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Header

from app.services.supabase_client import get_supabase
from app.schemas.disclosure import DisclosureResponse, DisclosureListResponse
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["disclosures"])

DART_BASE_URL = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo="

# ─── Company-name normalisation ─────────────────────────────────

_CORP_SUFFIX_RE = re.compile(
    r"(?:\(주\)|㈜|주식회사|\(株\)|\(유\)|\(영\)|\(자\)|Co\.,?\s*Ltd\.?|株式会社)\s*$"
)


def _normalise_corp_name(raw: str) -> str:
    """Strip corporate suffixes so '삼성전자(주)' → '삼성전자' for grouping."""
    name = raw.strip()
    name = _CORP_SUFFIX_RE.sub("", name).strip()
    return name


def _cleanest_name(candidates: list[str]) -> str:
    """Pick the shortest non-empty candidate as the display name."""
    cleaned = [n.strip() for n in candidates if n.strip()]
    if not cleaned:
        return ""
    return min(cleaned, key=len)


def _row_to_response(row: dict) -> dict:
    rcept_no = row.get("dart_rcept_no", "")
    return {
        "id": row.get("id", ""),
        "dart_rcept_no": rcept_no,
        "dart_url": f"{DART_BASE_URL}{rcept_no}",
        "ticker": row.get("ticker", ""),
        "company_name": _normalise_corp_name(row.get("company_name", "")),
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
        "signal_horizon": row.get("signal_horizon"),
        "cerebras_sentiment": row.get("cerebras_sentiment"),
        "cerebras_confidence": row.get("cerebras_confidence"),
        "cerebras_reason": row.get("cerebras_reason"),
        "llm_summary": row.get("llm_summary"),
        "key_metrics": row.get("key_metrics"),
        "llm_status": row.get("llm_status", "PENDING"),
        "created_at": row.get("created_at"),
    }


_SELECT_COLS = (
    "id,dart_rcept_no,ticker,company_name,title,published_at,"
    "category,sub_type,sub_rule_id,dvi_score,impact_level,risk_flag,"
    "is_feed_visible,deceptive_pattern_detected,momentum_authenticity,"
    "signal_horizon,cerebras_sentiment,cerebras_confidence,cerebras_reason,"
    "llm_summary,key_metrics,llm_status,created_at"
)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

async def _resolve_user_from_token(authorization: str = Header(None)) -> Optional[dict]:
    """If the request carries a valid Supabase JWT, verify via Supabase Auth API and return user with plan."""
    if not authorization:
        return None
    try:
        from app.services.supabase_client import get_public_client
        token = authorization.replace("Bearer ", "")
        client = get_public_client()
        user_resp = client.auth.get_user(token)
        auth_user = user_resp.user
        if not auth_user:
            return None
        email = auth_user.email or ""
        if not email:
            return None
        supabase = get_supabase()
        user_row = (
            supabase.table("users")
            .select("id, plan, api_key")
            .eq("email", email)
            .maybe_single()
            .execute()
        )
        return user_row.data or None
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


@router.get("/company-suggest")
async def company_suggest(
    q: str = Query(..., min_length=1, max_length=100, description="회사명/종목코드 부분 검색"),
):
    """
    Autocomplete for company names and tickers.

    Searches both company_name and ticker (OR), deduplicates,
    and returns up to 10 distinct (company_name, ticker) pairs.
    """
    supabase = get_supabase()
    # Use PostgREST or_ filter to search both columns; Supabase-py does not
    # expose column-level DISTINCT, so fetch a generous pool and dedup below.
    or_filter = f"company_name.ilike.%{q}%,ticker.ilike.%{q}%"
    result = (
        supabase.table("disclosures")
        .select("company_name, ticker")
        .or_(or_filter)
        .limit(1000)
        .execute()
    )

    # Group by normalised name ONLY (not ticker), pick the most common ticker.
    # Sort by disclosure count (most searched → first), then alphabetically.
    groups: dict[str, dict] = {}
    for row in result.data or []:
        raw_name = (row.get("company_name") or "").strip()
        ticker = (row.get("ticker") or "").strip()
        if not raw_name or not ticker:
            continue
        norm = _normalise_corp_name(raw_name)
        if norm not in groups:
            groups[norm] = {"variants": [], "ticker_counts": {}, "count": 0}
        groups[norm]["variants"].append(raw_name)
        groups[norm]["count"] += 1
        groups[norm]["ticker_counts"][ticker] = groups[norm]["ticker_counts"].get(ticker, 0) + 1

    suggestions = []
    for norm, data in groups.items():
        best_ticker = max(data["ticker_counts"], key=data["ticker_counts"].get)
        suggestions.append({
            "company_name": _cleanest_name(data["variants"]),
            "ticker": best_ticker,
        })
    suggestions.sort(key=lambda x: (-groups[_normalise_corp_name(x["company_name"])]["count"], x["company_name"]))
    return {"suggestions": suggestions[:10]}


@router.get("/history")
async def get_history(
    q: Optional[str] = Query(None, description="통합 검색 (회사명+종목코드 OR 부분일치)"),
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

    Supports: q (unified search across ticker+company_name), ticker,
    company_name, category, score range, date range, risk_flag.
    """
    supabase = get_supabase()
    query = supabase.table("disclosures").select(_SELECT_COLS, count="exact")

    if q:
        query = query.or_(f"company_name.ilike.%{q}%,ticker.ilike.%{q}%")
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
    Uses Cerebras for analysis.
    """
    if not user or user.get("plan") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    supabase = get_supabase()

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
    ticker = row.get("ticker", "")
    corp_name = row.get("company_name", "")
    title = row.get("title", "")
    raw_text = row.get("raw_text", "")
    score = row.get("dvi_score", 0)

    brief = score < 80

    from app.services.cerebras_llm import analyze_disclosure as cerebras_analyze
    llm_result = await cerebras_analyze(
        ticker=ticker,
        company_name=corp_name,
        title=title,
        raw_text=raw_text,
        brief=brief,
    )

    if llm_result.llm_summary == "LLM 분석 실패":
        logger.error(f"LLM analysis failed for {disclosure_id}: fallback triggered")
        raise HTTPException(
            status_code=502,
            detail="LLM analysis failed — Cerebras API error",
        )

    update_data = {
        "llm_summary": llm_result.llm_summary[:8000],
        "key_metrics": [m.model_dump() for m in llm_result.key_metrics],
        "llm_raw_response": llm_result.model_dump(),
        "llm_status": "DONE",
    }

    from app.services.rules_engine import _is_ambiguous_title
    if _is_ambiguous_title(title):
        from app.services.cerebras_llm import analyze_ambiguity
        try:
            cerebras_result = await analyze_ambiguity(
                ticker=ticker, company_name=corp_name,
                title=title, raw_text=raw_text,
            )
            sentiment_map = {"POSITIVE": "positive", "NEGATIVE": "negative", "NEUTRAL": "neutral"}
            update_data["cerebras_sentiment"] = sentiment_map.get(cerebras_result.sentiment, "neutral")
            update_data["cerebras_confidence"] = cerebras_result.confidence
            update_data["cerebras_reason"] = cerebras_result.reason[:500]
            if cerebras_result.horizon in ("SHORT_TERM", "LONG_TERM"):
                update_data["signal_horizon"] = cerebras_result.horizon
        except Exception as e:
            logger.warning(f"Cerebras ambiguity analysis failed for {disclosure_id}: {e}")

    supabase.table("disclosures").update(update_data).eq(
        "id", disclosure_id
    ).execute()

    logger.info(f"Manual LLM analysis triggered for {disclosure_id}")
    return {"message": "LLM analysis completed", "summary": llm_result.llm_summary[:200]}


# ---------------------------------------------------------------------------
# /reprocess — Batch LLM re-analysis for disclosures missing analysis
# ---------------------------------------------------------------------------


@router.post("/reprocess")
async def reprocess_missing_llm(
    limit: int = 50,
    min_score: int = 0,
    user: Optional[dict] = Depends(get_premium_user),
):
    """
    Re-run LLM + Cerebras analysis for disclosures that are missing it.
    Admin-only. Processes up to `limit` disclosures per call.
    Use min_score=80 to target only high-scoring disclosures.
    """
    if not user or user.get("plan") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    supabase = get_supabase()

    # Fetch PENDING or null-summary disclosures
    result = (
        supabase.table("disclosures")
        .select("id,dart_rcept_no,ticker,company_name,title,raw_text,dvi_score,category,risk_flag,llm_status,llm_summary")
        .or_("llm_status.eq.PENDING,llm_summary.is.null")
        .order("published_at", desc=True)
        .limit(limit)
        .execute()
    )
    rows = list(result.data or [])

    # Also fetch "LLM 분석 실패" disclosures (old Groq failures) — separate query
    failed_result = (
        supabase.table("disclosures")
        .select("id,dart_rcept_no,ticker,company_name,title,raw_text,dvi_score,category,risk_flag,llm_status,llm_summary")
        .eq("llm_status", "DONE")
        .eq("llm_summary", "LLM 분석 실패")
        .order("published_at", desc=True)
        .limit(limit)
        .execute()
    )
    rows.extend(failed_result.data or [])

    # Deduplicate by dart_rcept_no
    seen = set()
    deduped = []
    for row in rows:
        rn = row.get("dart_rcept_no", "")
        if rn not in seen:
            seen.add(rn)
            deduped.append(row)
    rows = deduped

    if not rows:
        return {"message": "No disclosures need reprocessing", "processed": 0}

    processed = 0
    skipped = 0
    errors = 0

    for row in rows:
        title = row.get("title", "")
        category = row.get("category", "")
        risk_flag = row.get("risk_flag", "")
        score = row.get("dvi_score", 0) or 0
        existing_summary = row.get("llm_summary")

        # Skip administrative disclosures
        if category == "ADMINISTRATIVE":
            skipped += 1
            continue
        # Skip trap disclosures (non-clean risk flags)
        if risk_flag and risk_flag != "CLEAN":
            skipped += 1
            continue
        # Skip if already has a real summary (not failure placeholder)
        if existing_summary and "실패" not in existing_summary:
            skipped += 1
            continue
        # Skip if below min_score
        if score < min_score:
            skipped += 1
            continue

        rcept_no = row.get("dart_rcept_no", "")
        ticker = row.get("ticker", "")
        corp_name = row.get("company_name", "")
        raw_text = row.get("raw_text", "")

        try:
            brief = score < 80

            from app.services.cerebras_llm import analyze_disclosure as cerebras_analyze
            llm_result = await cerebras_analyze(
                ticker=ticker,
                company_name=corp_name,
                title=title,
                raw_text=raw_text,
                brief=brief,
            )

            if llm_result.llm_summary and llm_result.llm_summary != "LLM 분석 실패":
                update_data = _clean_payload({
                    "llm_summary": llm_result.llm_summary[:8000],
                    "key_metrics": [m.model_dump() for m in llm_result.key_metrics],
                    "llm_status": "DONE",
                })
                supabase.table("disclosures").update(update_data).eq(
                    "dart_rcept_no", rcept_no
                ).execute()
                processed += 1
                logger.info(f"Reprocessed LLM for {rcept_no}: {title[:40]}")
            else:
                errors += 1
                logger.warning(f"LLM returned failure for {rcept_no}")

        except Exception as e:
            errors += 1
            logger.error(f"Reprocess failed for {rcept_no}: {e}")

    return {
        "message": f"Batch reprocess complete",
        "processed": processed,
        "skipped": skipped,
        "errors": errors,
    }
