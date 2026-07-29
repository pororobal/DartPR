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

# ─── DVI score factor labels ────────────────────────────────────

_SCORE_FACTOR_LABELS = {
    # Category base
    "SHAREHOLDER_RETURN": "주주환원/지배구조",
    "CAPITAL_RAISING": "자금조달",
    "EARNINGS": "실적/재무",
    "BIOTECH": "바이오/제약",
    "BUSINESS_CONTRACT": "영업계약",
    "DELISTING_RISK": "상장위험",
    "ADMINISTRATIVE": "행정공시",
    # Sub-rule reasons
    "MA_AUDITOR_CHANGED": "감사인 변경 — 회계 정책 변경 가능성",
    "MA_CEO_CHANGED": "대표이사 변경 — 경영진 교체",
    "MA_MAJOR_CHANGE_GENERAL": "최대주주 변경",
    "MA_MAJOR_CHANGE_CONGLO_FIRST": "최대주주 변경(대기업 계열 편입)",
    "MA_MAJOR_CHANGE_NEWLY_FORMED": "최대주주 변경(신설법인 → 불확실성)",
    "MA_MERGER": "합병",
    "MA_MANAGEMENT_DISPUTE": "경영권 분쟁 — 최대 영향 이벤트",
    "MA_BLOCK_TRADE": "최대주주 장내매도",
    "MA_BULK_HOLDING_MANAGEMENT": "대량보유 + 경영참여",
    "MA_BULK_HOLDING_INVESTMENT": "대량보유(단순투자) — 노이즈",
    "MA_ACTIVIST": "행동주의 펀드 등장",
    "MA_PROXY_FIGHT": "위임장 대결",
    "MA_EGM_DISPUTE": "임시주총(경영권 분쟁 동반)",
    "MA_EGM_GENERAL": "임시주총 소집",
    "MA_SPLIT_WITH_LISTING": "물적분할 + 상장 — 주주가치 훼손 우려",
    "MA_OVERSEAS_LISTING": "해외증시 상장",
    "MA_EQUITY_ACQUISITION": "타법인 지분 양수",
    "MA_BUSINESS_TRANSFER": "영업양수도",
    "MA_SHARE_EXCHANGE": "주식교환/스왑",
    "MA_DEBT_ASSUMPTION": "채무인수 — 자금부담 증가",
    "MA_DEBT_GUARANTEE": "채무보증 — 우발채무 증가",
    "MA_COLLATERAL_PROVISION": "담보제공",
    "MA_DEBT_TO_EQUITY": "출자전환 — 부실기업 구조조정",
    "MA_DEBT_FORGIVENESS": "채무면제 — 파산 직전",
    "SHAREHOLDER_FIRST_BUYBACK_CANCEL": "최초 자사주 소각 — 강력한 주주환원",
    "SHAREHOLDER_REPEAT_BUYBACK_CANCEL": "자사주 추가 소각",
    "SHAREHOLDER_OPEN_MARKET_BUYBACK": "자사주 공개매수 — 가장 강력한 호재",
    "SHAREHOLDER_BUYBACK_ONLY": "자사주 취득(소각 미확정)",
    "SHAREHOLDER_DISPOSAL_OPERATING": "자사주 처분 — 운영자금 목적",
    "SHAREHOLDER_DISPOSAL_STOCK_OPTION": "자사주 처분(주식매수선택권)",
    "SHAREHOLDER_TREASURY_COLLATERAL": "자사주 담보제공 — 자금난 시그널",
    "SHAREHOLDER_MAJOR_PLEDGE": "최대주주 지분 담보 — 자금 사정 악화",
    "SHAREHOLDER_FIRST_DIVIDEND": "최초 배당",
    "SHAREHOLDER_DIVIDEND_HIGH": "고배당(5% 이상)",
    "SHAREHOLDER_DIVIDEND_LOW": "배당",
    "SHAREHOLDER_STOCK_DIVIDEND": "주식배당 — 현금 부족 시그널",
    "SHAREHOLDER_TREASURY_TRUST": "자사주 신탁계약",
    "SHAREHOLDER_GENERAL": "일반 주주환원",
    "CAPITAL_RAISING_THIRD_PARTY_CONGLO": "제3자배정(대기업) — 자금력+신뢰도",
    "CAPITAL_RAISING_THIRD_PARTY_GENERAL": "제3자배정 유상증자",
    "CAPITAL_RAISING_THIRD_PARTY_INSIDER": "제3자배정(내부자)",
    "CAPITAL_RAISING_THIRD_PARTY_PE": "제3자배정(PE/조합) — 일반보다 저평가",
    "CAPITAL_RAISING_THIRD_PARTY_UNDISCLOSED": "제3자배정(대상 미공개) — 불확실성",
    "CAPITAL_RAISING_RIGHTS_OFFERING": "주주배정 유상증자 — 희석 부담",
    "CAPITAL_RAISING_FREE_INCREASE": "무상증자 — 주주친화적",
    "CAPITAL_RAISING_CB_REFIXING": "CB 리픽싱 — 전환가 하향 = 희석 ↑",
    "CAPITAL_RAISING_CB_EARLY_REDEEM": "CB 조기상환 — 재무 부담 해소",
    "CAPITAL_RAISING_CB_CONVERTED": "CB 전환청구 — 실제 희석 발생",
    "CAPITAL_RAISING_CB_PRICE_UP": "CB 전환가 상향",
    "CAPITAL_RAISING_WARRANT_EXERCISED": "신주인수권(BW) 행사",
    "CAPITAL_RAISING_CB_FACILITY": "CB 발행(시설자금) — 성장 투자",
    "CAPITAL_RAISING_CB_WORKING": "CB 발행(운영자금) — 자금 사정",
    "CAPITAL_RAISING_DEBT_ISSUANCE": "일반 사채발행",
    "CAPITAL_RAISING_FREE_REDUCTION": "무상감자 — 사실상 손실 인정",
    "CAPITAL_RAISING_PAID_REDUCTION": "유상감자 — 자본 효율화",
    "CAPITAL_RAISING_WITHDRAWN": "유상증자 철회",
    "CAPITAL_RAISING_DELAYED_PAYMENT": "납입 지연 — 자금조달 차질",
    "BIOTECH_FDA_APPROVAL": "FDA/식약처 승인 — 최대 호재",
    "BIOTECH_CLINICAL_HOLD": "임상 중지 — 파이프라인 리스크",
    "BIOTECH_PHASE3_NDA": "임상 3상/품목허가 신청",
    "BIOTECH_TECH_TRANSFER_AMOUNT": "기술이전(금액 공개) — 가치 실현",
    "BIOTECH_TECH_TRANSFER_NO_AMOUNT": "기술이전(금액 미공개)",
    "BIOTECH_TECH_RETURN": "기술반환 — 파이프라인 실패",
    "EARNINGS_LOSS_TO_PROFIT_3Q": "3분기 연속 흑자전환 — 실적 턴어라운드 확정",
    "EARNINGS_LOSS_TO_PROFIT_1Q": "흑자전환 — 추세 확인 필요",
    "EARNINGS_LOSS_TO_PROFIT_NO_HISTORY": "흑자전환(전력 부족)",
    "EARNINGS_LOSS_TO_PROFIT_NON_OP": "영업외손익 흑자전환 — 일회성",
    "EARNINGS_PROFIT_TO_LOSS_3Q": "3분기 연속 적자전환 — 구조적 악화",
    "EARNINGS_PROFIT_TO_LOSS_1Q": "적자전환",
    "EARNINGS_LOSS_CONTINUED_4Q": "4분기 연속 적자 — 심각",
    "EARNINGS_LOSS_CONTINUED": "적자 지속",
    "EARNINGS_REVENUE_INCREASE": "매출 증가",
    "EARNINGS_REVENUE_DECREASE": "매출 감소",
    "EARNINGS_OP_PROFIT_IMPROVING": "영업이익 개선",
    "EARNINGS_OP_PROFIT_WORSENING": "영업이익 악화",
    "EARNINGS_AUDIT_UNQUALIFIED": "감사의견 적정 — 회계 투명",
    "BUSINESS_CONTRACT_TERMINATED": "계약 해지 — 매출 감소 리스크",
    "BUSINESS_CONTRACT_MODIFIED": "계약 조건 변경(감액)",
    "HARD_FAIL": "위험 키워드 탐지 — 즉시 확인 필요",
    "DELISTING_RISK": "상장폐지 리스크",
    "RISK_GOING_CONCERN": "계속기업 불확실성",
    "RISK_CAPITAL_IMPAIRMENT": "자본잠식",
    "RISK_MANAGEMENT_ISSUE": "관리종목 지정 우려",
    "RISK_LISTING_REVIEW": "상장적격성 심사",
    "RISK_SERIOUS_ACCIDENT": "중대재해 발생",
    "RISK_MARKET_WARNING_DANGER": "투자위험 종목",
    "RISK_MARKET_WARNING_CAUTION": "투자경고 종목",
    "RISK_MARKET_WARNING_ATTENTION": "투자주의 종목",
}


def _get_score_factors(row: dict) -> list[str]:
    """Compute human-readable score breakdown from DB row."""
    factors = []
    cat = row.get("category") or ""
    sub_id = row.get("sub_rule_id") or ""
    score = row.get("dvi_score") or 0
    impact = row.get("impact_level") or ""
    risk = row.get("risk_flag") or ""

    # Category factor
    cat_label = _SCORE_FACTOR_LABELS.get(cat, cat)
    if cat in ("DELISTING_RISK", "ADMINISTRATIVE"):
        factors.append(f"카테고리: {cat_label}")
    else:
        factors.append(f"카테고리: {cat_label} — 기준 점수 30")

    # Sub-rule factor
    if sub_id and sub_id not in ("OTHER_DEFAULT", "ADMIN_DISCLOSURE", "SPV_ENTITY"):
        sub_label = _SCORE_FACTOR_LABELS.get(sub_id, sub_id)
        if score >= 60:
            factors.append(f"핵심 이벤트: {sub_label}")
        elif score >= 30:
            factors.append(f"탐지: {sub_label}")
        else:
            factors.append(f"리스크: {sub_label}")

    # Risk flag
    if risk == "HIGH_RISK_TRAP":
        factors.append("⚠ 고위험 패턴 — 투자자 함정 주의")
    elif risk == "CLEAN":
        pass

    # Impact level
    impact_labels = {"HIGH_IMPACT": "고영향", "NORMAL": "보통", "LOW_IMPACT": "저영향"}
    il = impact_labels.get(impact, impact)
    factors.append(f"영향도: {il}")

    return factors


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
        "score_factors": _get_score_factors(row),
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
        .eq("is_feed_visible", True)
        .or_(or_filter)
        .limit(10)
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

    Only returns feed-visible disclosures (excludes SPVs, administrative noise).
    """
    supabase = get_supabase()
    query = (
        supabase.table("disclosures")
        .select(_SELECT_COLS, count="estimated")
        .eq("is_feed_visible", True)
    )

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
        .select("id,dart_rcept_no,company_name,title,raw_text,ticker")
        .execute()
    )
    rows = result.data or []
    updated = 0
    skipped = 0

    for row in rows:
        title = row.get("title", "")
        raw_text = row.get("raw_text", "")
        ticker = row.get("ticker", "")
        corp_name = row.get("company_name", "")

        score_result = evaluate_disclosure(
            title=title, raw_text=raw_text, ticker=ticker, supabase=supabase,
            corp_name=corp_name,
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
    Uses Groq LLM for summarization + ambiguity analysis.
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

    from app.services.groq_service import analyze_disclosure as groq_analyze
    llm_result = await groq_analyze(
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
            detail="LLM analysis failed — API error",
        )

    update_data = {
        "llm_summary": llm_result.llm_summary[:8000],
        "key_metrics": [m.model_dump() for m in llm_result.key_metrics],
        "llm_raw_response": llm_result.model_dump(),
        "llm_status": "DONE",
    }

    from app.services.rules_engine import _is_ambiguous_title
    if _is_ambiguous_title(title):
        from app.services.groq_service import analyze_ambiguity
        try:
            cerebras_result = await analyze_ambiguity(
                ticker=ticker, company_name=corp_name,
                title=title, raw_text=raw_text,
            )
            sentiment_map = {"BENEFICIAL": "beneficial", "ADVERSE": "adverse", "NEUTRAL": "neutral"}
            update_data["cerebras_sentiment"] = sentiment_map.get(cerebras_result.impact_direction, "neutral")
            update_data["cerebras_confidence"] = cerebras_result.confidence
            update_data["cerebras_reason"] = cerebras_result.reason[:500]
            if cerebras_result.horizon in ("SHORT_TERM", "LONG_TERM"):
                update_data["signal_horizon"] = cerebras_result.horizon
        except Exception as e:
            logger.warning(f"Ambiguity analysis failed for {disclosure_id}: {e}")

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

            from app.services.groq_service import analyze_disclosure as groq_analyze
            llm_result = await groq_analyze(
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
