"""
Intro page examples generator.

Daily pipeline at 20:00 KST:
1. Query today's disclosures from Supabase (published_at in KST)
2. Select 3 representative examples: 2 high-score positive + 1 risk
3. Upsert into intro_examples table keyed by target_date
"""

import logging
from datetime import datetime, date, timezone, timedelta

from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))


def _kst_now() -> datetime:
    return datetime.now(KST)


def _kst_today() -> date:
    return _kst_now().date()


async def run_intro_examples_pipeline() -> list[dict]:
    """Query today's disclosures, curate 3 examples, upsert into intro_examples."""
    today = _kst_today()
    supabase = get_supabase()

    # Build KST range: today 00:00:00 KST ~ 23:59:59 KST
    day_start = datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=KST)
    day_end = datetime(today.year, today.month, today.day, 23, 59, 59, 999999, tzinfo=KST)

    # Query all visible disclosures from today
    result = (
        supabase.table("disclosures")
        .select(
            "dart_rcept_no, ticker, company_name, title, category, sub_rule_id, "
            "dvi_score, risk_flag, llm_summary, signal_horizon, published_at"
        )
        .gte("published_at", day_start.isoformat())
        .lte("published_at", day_end.isoformat())
        .eq("is_feed_visible", True)
        .order("dvi_score", desc=True)
        .execute()
    )

    rows = result.data or []
    if not rows:
        logger.info("No visible disclosures today — intro examples will be empty")
        curated = []
    else:
        curated = _curate_examples(rows)

    # Upsert by target_date
    payload = {
        "target_date": today.isoformat(),
        "examples": curated,
        "updated_at": _kst_now().isoformat(),
    }
    supabase.table("intro_examples").upsert(payload, on_conflict="target_date").execute()

    logger.info("intro_examples updated for %s (%d items)", today.isoformat(), len(curated))
    return curated


def _curate_examples(rows: list[dict]) -> list[dict]:
    """Pick 2 positive (highest score, non-risk) + 1 risk/low-score."""
    risk = []
    positive = []
    for r in rows:
        cat = (r.get("category") or "").upper()
        risk_flag = (r.get("risk_flag") or "").upper()
        score = r.get("dvi_score") or 0
        # Risk candidates: DELISTING_RISK category or HIGH_RISK_TRAP or score < 15
        if cat == "DELISTING_RISK" or risk_flag == "HIGH_RISK_TRAP" or score < 15:
            risk.append(r)
        else:
            positive.append(r)

    # Sort positive by dvi_score descending, pick top 2
    positive_sorted = sorted(positive, key=lambda x: -(x.get("dvi_score") or 0))
    picked_positive = positive_sorted[:2]

    # Pick 1 risk (lowest score first = most severe)
    risk_sorted = sorted(risk, key=lambda x: (x.get("dvi_score") or 100))
    picked_risk = risk_sorted[:1] if risk_sorted else []

    combined = picked_positive + picked_risk
    # Map to output shape matching ExampleCardProps
    return [_build_example(r) for r in combined]


def _build_example(row: dict) -> dict:
    """Map a Supabase disclosure row to intro example shape."""
    score = row.get("dvi_score") or 0
    cat = (row.get("category") or "").upper()
    risk_flag = (row.get("risk_flag") or "").upper()
    horizon = row.get("signal_horizon") or ""

    # Determine signal label + icon + color (mirrors DisclosureCard getSignal)
    is_trap = risk_flag and risk_flag != "CLEAN"
    summary = row.get("llm_summary") or _fallback_summary(row)
    title = row.get("title") or ""

    if cat == "ADMINISTRATIVE":
        signal = {"icon": "⚪", "label": "행정 공시", "color": "text-gray-400"}
    elif is_trap or score == 0:
        signal = {"icon": "🔴", "label": "위험", "color": "text-red-400"}
    elif score >= 90:
        signal = {"icon": "🟢", "label": _signal_label(cat, "긍정"), "color": "text-green-400"}
    elif score >= 70:
        signal = {"icon": "🟡", "label": _signal_label(cat, "긍정"), "color": "text-yellow-400"}
    elif cat == "DELISTING_RISK":
        signal = {"icon": "🔴", "label": "상장유지 리스크", "color": "text-red-400"}
    elif score >= 30:
        signal = {"icon": "⚪", "label": "중립", "color": "text-gray-400"}
    else:
        signal = {"icon": "🟠", "label": "주의", "color": "text-orange-400"}

    # badge mirrors categoryChip from DisclosureCard
    badge = _badge_label(cat)

    return {
        "ticker": row.get("ticker") or "",
        "company": row.get("company_name") or "",
        "time": _format_time(row.get("published_at")),
        "title": title,
        "score": score,
        "signal": signal,
        "summary": summary,
        "badge": badge,
    }


def _signal_label(cat: str, fallback: str) -> str:
    labels = {
        "CAPITAL_RAISING": "자본조달",
        "BIOTECH": "임상 이벤트",
        "BUSINESS_CONTRACT": "계약 이벤트",
        "EARNINGS": "실적",
        "SHAREHOLDER_RETURN": "주주환원",
        "DELISTING_RISK": "상장유지 리스크",
    }
    return labels.get(cat, fallback)


def _badge_label(cat: str) -> str:
    labels = {
        "ADMINISTRATIVE": "행정",
        "CAPITAL_RAISING": "자금조달",
        "BIOTECH": "바이오",
        "BUSINESS_CONTRACT": "영업계약",
        "EARNINGS": "실적",
        "SHAREHOLDER_RETURN": "주주환원",
        "DELISTING_RISK": "상장위험",
    }
    return labels.get(cat, "기타")


def _fallback_summary(row: dict) -> str:
    """When LLM_summary is null, build a basic summary from title + category."""
    title = row.get("title") or ""
    cat = (row.get("category") or "").upper()
    prefix = {
        "SHAREHOLDER_RETURN": "주주가치 제고와 관련된 공시입니다.",
        "BIOTECH": "바이오 연구개발과 관련된 공시입니다.",
        "CAPITAL_RAISING": "자금 조달과 관련된 공시입니다.",
        "BUSINESS_CONTRACT": "영업 계약과 관련된 공시입니다.",
        "EARNINGS": "실적과 관련된 공시입니다.",
        "DELISTING_RISK": "상장 유지와 관련된 리스크 공시입니다.",
    }
    cat_desc = prefix.get(cat, "공시사항입니다.")
    return f"{title}. {cat_desc}"


def _format_time(published_at) -> str:
    """Format to 'MM. DD. 오후/오전 HH:MM' KST."""
    if not published_at:
        return ""
    if isinstance(published_at, str):
        try:
            dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        except ValueError:
            return published_at[:16]
    else:
        dt = published_at
    # Convert to KST
    kst_dt = dt.astimezone(KST)
    hour = kst_dt.hour
    minute = kst_dt.minute
    ampm = "오전" if hour < 12 else "오후"
    h12 = hour % 12
    if h12 == 0:
        h12 = 12
    return f"{kst_dt.month:02d}. {kst_dt.day:02d}. {ampm} {h12:02d}:{minute:02d}"
