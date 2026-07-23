"""
OpenDART API poller service.

Background scheduler that:
1. Polls OpenDART API every N seconds
2. Fetches new disclosures
3. Runs hard-fail filter
4. Computes DVI score via rules engine
5. Stores to Supabase (INSERT)
6. Triggers Groq LLM enrichment asynchronously → UPDATE
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.services.supabase_client import get_supabase
from app.services.rules_engine import check_hard_fail, compute_score

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

_scheduler: Optional[AsyncIOScheduler] = None
_is_running = False


async def start_poller():
    """Start the background DART polling scheduler."""
    global _scheduler, _is_running
    if _is_running:
        return

    if not settings.opendart_api_key:
        logger.warning("OPENDART_API_KEY not set — poller not started")
        return

    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        poll_dart_once,
        "interval",
        seconds=settings.poll_interval_seconds,
        id="dart_poller",
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc),  # run immediately on start
    )
    _scheduler.start()
    _is_running = True
    logger.info(
        f"DART poller started (interval={settings.poll_interval_seconds}s)"
    )


async def stop_poller():
    """Stop the background DART polling scheduler."""
    global _scheduler, _is_running
    if _scheduler and _is_running:
        _scheduler.shutdown(wait=False)
        _is_running = False
        logger.info("DART poller stopped")


# ---------------------------------------------------------------------------
# OpenDART API client
# ---------------------------------------------------------------------------

OPENDART_LIST_URL = "https://opendart.fss.or.kr/api/list.json"
OPENDART_DOCUMENT_URL = "https://opendart.fss.or.kr/api/document.xml"


async def _fetch_disclosure_list() -> list[dict]:
    """
    Fetch 공시목록 from OpenDART API for today.
    Returns list of disclosure items.
    """
    today = datetime.now(timezone.utc)
    date_str = today.strftime("%Y%m%d")

    params = {
        "crtfc_key": settings.opendart_api_key,
        "page_no": 1,
        "page_count": 100,
        "bgn_de": date_str,
        "end_de": date_str,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(OPENDART_LIST_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "000":
                logger.warning(
                    f"OpenDART API error: {data.get('message', 'unknown')}"
                )
                return []

            return data.get("list", [])

        except httpx.HTTPError as e:
            logger.error(f"OpenDART HTTP error: {e}")
            return []
        except Exception as e:
            logger.error(f"OpenDART fetch error: {e}", exc_info=True)
            return []


async def _fetch_document_text(rcept_no: str) -> Optional[str]:
    """
    Fetch the full document text (XML) for a given 접수번호.
    Returns raw text or None on failure.
    """
    params = {
        "crtfc_key": settings.opendart_api_key,
        "rcept_no": rcept_no,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(OPENDART_DOCUMENT_URL, params=params)
            resp.raise_for_status()
            return resp.text
        except httpx.HTTPError as e:
            logger.warning(
                f"Document fetch failed for {rcept_no}: {e}"
            )
            return None
        except Exception as e:
            logger.error(
                f"Document fetch error for {rcept_no}: {e}", exc_info=True
            )
            return None


# ---------------------------------------------------------------------------
# Disclosure processing pipeline
# ---------------------------------------------------------------------------

async def _process_disclosure(item: dict):
    """
    Process a single disclosure item through the pipeline:
    1. Check hard-fail
    2. Compute DVI score
    3. Insert to Supabase
    4. If no hard-fail, trigger LLM enrichment
    """
    rcept_no = item.get("rcept_no", "")
    ticker = item.get("corp_code", "")  # OpenDART uses corp_code
    corp_name = item.get("corp_name", "")
    title = item.get("report_nm", "").strip()
    rcept_dt = item.get("rcept_dt", "")

    # Parse date
    try:
        published_at = datetime.strptime(str(rcept_dt), "%Y%m%d").replace(
            tzinfo=timezone.utc
        )
    except (ValueError, TypeError):
        published_at = datetime.now(timezone.utc)

    # Fetch full document text
    raw_text = await _fetch_document_text(rcept_no)
    if raw_text is None:
        raw_text = f"{corp_name} - {title}"  # fallback if document fetch fails

    if not rcept_no:
        logger.warning("Disclosure item missing rcept_no — skipping")
        return

    # Check if already exists in DB
    supabase = get_supabase()
    existing = (
        supabase.table("disclosures")
        .select("id")
        .eq("dart_rcept_no", rcept_no)
        .execute()
    )
    if existing.data and len(existing.data) > 0:
        logger.debug(f"Disclosure {rcept_no} already exists — skipping")
        return

    # 1. Hard-fail check
    hard_fail = check_hard_fail(raw_text)
    skip_llm = hard_fail.detected

    # 2. Compute score without LLM for initial insert.
    #    Use keyword-based category + flags for content-aware scoring.
    category, sub_rule_flags = _guess_category(title, raw_text)
    score_result = compute_score(category, sub_rule_flags)

    # Build insert payload — sanitize raw_text for PostgreSQL safety
    safe_raw_text = raw_text[:50000].encode("utf-8", errors="replace").decode("utf-8")
    insert_data = {
        "dart_rcept_no": rcept_no,
        "ticker": ticker,
        "company_name": corp_name,
        "title": title,
        "raw_text": safe_raw_text,
        "published_at": published_at.isoformat(),
        "category": category,
        "sub_rule_id": score_result.sub_rule_id,
        "dvi_score": score_result.dvi_score,
        "impact_level": score_result.impact_level,
        "risk_flag": "HIGH_RISK_TRAP" if hard_fail.detected else score_result.risk_flag,
        "deceptive_pattern_detected": True if hard_fail.detected else None,
        "momentum_authenticity": "LOW" if hard_fail.detected else None,
        "llm_status": "DONE" if skip_llm else "PENDING",
        "is_feed_visible": score_result.is_feed_visible or hard_fail.detected,
    }

    try:
        supabase.table("disclosures").insert(insert_data).execute()
        logger.info(
            f"Inserted disclosure {rcept_no}: {corp_name} - {title}"
            f" (score={score_result.dvi_score}, hard_fail={hard_fail.detected})"
        )
    except Exception as e:
        logger.error(f"Supabase insert failed for {rcept_no}: {e}")
        return

    # 3. If not hard-fail, trigger LLM enrichment asynchronously
    if not skip_llm:
        asyncio.create_task(_enrich_with_llm(rcept_no, ticker, corp_name, title, raw_text))


async def _enrich_with_llm(
    rcept_no: str,
    ticker: str,
    corp_name: str,
    title: str,
    raw_text: str,
):
    """
    Call Groq LLM to analyze disclosure, then UPDATE the row with enriched data.
    """
    try:
        from app.services.groq_llm import analyze_disclosure

        llm_result = await analyze_disclosure(
            ticker=ticker,
            company_name=corp_name,
            title=title,
            raw_text=raw_text,
        )

        # Compute final score with LLM-provided flags
        score_result = compute_score(
            llm_result.category,
            llm_result.sub_rule_flags.model_dump(),
        )

        # Build update payload
        update_data = {
            "category": llm_result.category,
            "sub_rule_id": score_result.sub_rule_id,
            "dvi_score": score_result.dvi_score,
            "impact_level": score_result.impact_level,
            "risk_flag": score_result.risk_flag,
            "deceptive_pattern_detected": llm_result.deceptive_pattern_detected,
            "momentum_authenticity": llm_result.momentum_authenticity,
            "llm_summary": llm_result.llm_summary,
            "key_metrics": [m.model_dump() for m in llm_result.key_metrics],
            "llm_raw_response": llm_result.model_dump(),
            "llm_status": "DONE",
            "is_feed_visible": score_result.is_feed_visible
            or score_result.risk_flag == "HIGH_RISK_TRAP",
        }

        supabase = get_supabase()
        supabase.table("disclosures").update(update_data).eq(
            "dart_rcept_no", rcept_no
        ).execute()

        logger.info(
            f"LLM enrichment done for {rcept_no}: "
            f"category={llm_result.category}, score={score_result.dvi_score}"
        )

    except Exception as e:
        logger.error(f"LLM enrichment failed for {rcept_no}: {e}", exc_info=True)
        # Mark as DONE even on failure so frontend stops showing spinner
        try:
            supabase = get_supabase()
            supabase.table("disclosures").update({
                "llm_status": "DONE",
                "llm_summary": "LLM 분석 실패",
            }).eq("dart_rcept_no", rcept_no).execute()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Category guesser (pre-LLM fallback)
# ---------------------------------------------------------------------------

def _guess_category(title: str, raw_text: str) -> tuple[str, dict]:
    """
    Keyword-based category guess using the disclosure title only.
    Returns (category, sub_rule_flags) for more granular scoring.
    The report title (report_nm) is the most reliable signal for categorization.
    """
    t = title.upper()

    # Delisting risk — highest priority
    if any(kw in t for kw in ["감사의견", "횡령", "배임", "감자", "상장폐지",
                               "관리종목지정우려", "상장적격성"]):
        return ("DELISTING_RISK", {"risk_flag": "HIGH_RISK_TRAP"})

    # Shareholder return
    if any(kw in t for kw in ["주식소각", "자기주식소각"]):
        return ("SHAREHOLDER_RETURN", {"sr_type": "BUYBACK_RETIREMENT"})
    if any(kw in t for kw in ["자사주취득", "자기주식취득"]):
        return ("SHAREHOLDER_RETURN", {"sr_type": "BUYBACK_ONLY"})
    if any(kw in t for kw in ["자기주식처분"]):
        return ("SHAREHOLDER_RETURN", {"sr_type": "BUYBACK_ONLY"})
    if any(kw in t for kw in ["최대주주변경"]):
        return ("SHAREHOLDER_RETURN", {"sr_type": "MAJOR_CHANGE"})
    if any(kw in t for kw in ["배당", "주주환원"]):
        return ("SHAREHOLDER_RETURN", {"sr_type": "DIVIDEND"})

    # Capital raising
    if any(kw in t for kw in ["유상증자", "주주배정"]):
        return ("CAPITAL_RAISING", {"cr_type": "RIGHTS_OFFERING"})
    if any(kw in t for kw in ["CB 발행", "BW 발행", "전환사채", "전환청구권",
                               "신주인수권", "3자배정"]):
        return ("CAPITAL_RAISING", {"cr_type": "CB_BW_THIRDPARTY"})

    # Business contract
    if any(kw in t for kw in ["단일판매", "공급계약", "판매계약", "수주"]):
        return ("BUSINESS_CONTRACT", {"bc_type": "SUPPLY_CONTRACT"})
    if any(kw in t for kw in ["무상증자"]):
        return ("BUSINESS_CONTRACT", {"bc_type": "FREE_ISSUE"})

    # Earnings — check sign first
    if any(kw in t for kw in ["적자전환", "적자지속", "영업손실", "당기순손실"]):
        return ("EARNINGS", {"er_sign": "NEGATIVE"})
    if any(kw in t for kw in ["흑자전환", "영업이익", "매출액증가", "실적개선"]):
        return ("EARNINGS", {"er_sign": "POSITIVE"})
    if any(kw in t for kw in ["감사보고서", "사업보고서", "반기보고서", "분기보고서"]):
        return ("EARNINGS", {"er_sign": "REGULAR_FILING"})
    if any(kw in t for kw in ["실적", "매출액"]):
        return ("EARNINGS", {"er_sign": "NEUTRAL"})

    # Legal / litigation
    if any(kw in t for kw in ["소송", "회생", "파산", "법정관리"]):
        return ("DELISTING_RISK", {"risk_flag": "HIGH_RISK_TRAP"})

    # M&A
    if any(kw in t for kw in ["합병결정", "분할합병", "포괄적주식교환"]):
        return ("EARNINGS", {"er_sign": "NEUTRAL", "event": "MERGER"})

    # Major shareholder reporting
    if any(kw in t for kw in ["대량보유", "주식등의대량보유"]):
        return ("EARNINGS", {"er_sign": "NEUTRAL", "event": "MAJOR_HOLDING"})

    # Biotech
    if any(kw in t for kw in ["임상", "FDA 승인", "품목허가", "신약", "기술이전"]):
        return ("BIOTECH", {})

    return ("EARNINGS", {"er_sign": "NEUTRAL"})


# ---------------------------------------------------------------------------
# Manual trigger
# ---------------------------------------------------------------------------

async def poll_dart_once():
    """
    Single poll cycle. Called by scheduler.
    Also exported for manual triggering via API.
    """
    logger.info("Polling DART API...")
    items = await _fetch_disclosure_list()

    if not items:
        logger.info("No new disclosures found")
        return

    logger.info(f"Found {len(items)} disclosures — processing...")

    # Process sequentially to avoid overwhelming APIs
    for item in items:
        await _process_disclosure(item)

    logger.info(f"Poll cycle complete: {len(items)} items processed")
