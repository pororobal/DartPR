"""
OpenDART API poller service.

Background scheduler pipeline:
1. Polls OpenDART API every N seconds
2. Fetches new disclosures
3. Step 1: Administrative check → skip scoring & LLM
4. Step 2: Fast-fail check → risk_flag=HIGH_RISK_TRAP, always visible, skip LLM
5. Step 3: Keyword category guess
6. Step 4: Full scoring (all §5 tables, DB history lookups)
7. Step 5: LLM enrichment ONLY if score >= FEED_VISIBILITY_THRESHOLD (80)
8. INSERT → Realtime broadcast
"""

import asyncio
import json
import logging
import re
import unicodedata
import zipfile
from io import BytesIO
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.services.supabase_client import get_supabase
from app.services.rules_engine import (
    check_administrative,
    check_hard_fail,
    evaluate_disclosure,
)

logger = logging.getLogger(__name__)

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
_UNICODE_NULL_ESCAPE_RE = re.compile(r"\\u0000", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")


def _clean_text(value: object, limit: int = 50000) -> str:
    """Normalize incoming text so Supabase/Postgres can store it safely."""
    if value is None:
        return ""

    text = str(value)
    text = unicodedata.normalize("NFC", text)
    text = text.encode("utf-8", errors="replace").decode("utf-8")
    text = _UNICODE_NULL_ESCAPE_RE.sub(" ", text)
    text = _CONTROL_CHAR_RE.sub(" ", text)
    text = text.replace("\u0000", " ")
    return text[:limit]


def _clean_payload(value: Any) -> Any:
    if isinstance(value, str):
        return _clean_text(value)
    if isinstance(value, list):
        return [_clean_payload(item) for item in value]
    if isinstance(value, dict):
        return {key: _clean_payload(item) for key, item in value.items()}
    return value


def _decode_bytes(data: bytes) -> str:
    for encoding in ("utf-8", "cp949", "euc-kr"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _strip_markup(text: str) -> str:
    return _TAG_RE.sub(" ", text)

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
        logger.warning("OPENDART_API_KEY not set -- poller not started")
        return

    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        poll_dart_once,
        "interval",
        seconds=settings.poll_interval_seconds,
        id="dart_poller",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        next_run_time=datetime.now(timezone.utc),
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
    today = datetime.now().astimezone()
    date_str = today.strftime("%Y%m%d")

    all_items: list[dict] = []
    page_no = 1
    page_count = 100

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            params = {
                "crtfc_key": settings.opendart_api_key,
                "page_no": page_no,
                "page_count": page_count,
                "bgn_de": date_str,
                "end_de": date_str,
            }

            try:
                resp = await client.get(OPENDART_LIST_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError as e:
                logger.error(f"OpenDART HTTP error (page {page_no}): {e}")
                break
            except Exception as e:
                logger.error(
                    f"OpenDART fetch error (page {page_no}): {e}",
                    exc_info=True,
                )
                break

            if data.get("status") != "000":
                logger.warning(
                    f"OpenDART API error (page {page_no}): "
                    f"{data.get('message', 'unknown')}"
                )
                break

            items = data.get("list", [])
            all_items.extend(items)
            logger.debug(
                f"Fetched page {page_no}: {len(items)} disclosures "
                f"(total: {len(all_items)})"
            )

            # Stop if fewer items than page_count (last page)
            if len(items) < page_count:
                break

            page_no += 1
            # Respect API rate limit: 1 req/s
            await asyncio.sleep(1)

    return all_items


async def _fetch_document_text(rcept_no: str) -> Optional[str]:
    params = {
        "crtfc_key": settings.opendart_api_key,
        "rcept_no": rcept_no,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(OPENDART_DOCUMENT_URL, params=params)
            resp.raise_for_status()
            content = resp.content

            if zipfile.is_zipfile(BytesIO(content)):
                chunks: list[str] = []
                with zipfile.ZipFile(BytesIO(content)) as archive:
                    for name in archive.namelist():
                        if name.endswith("/"):
                            continue
                        data = archive.read(name)
                        data = data.replace(b"\x00", b"")
                        chunks.append(_decode_bytes(data))
                return _strip_markup("\n".join(chunks))

            if b"\x00" in content:
                logger.warning(
                    f"Document response contains binary nulls for {rcept_no}; "
                    "stripping nulls and continuing"
                )
                content = content.replace(b"\x00", b"")
                if content.strip():
                    return _strip_markup(_decode_bytes(content))
                return None

            return _strip_markup(_decode_bytes(content))
        except httpx.HTTPError as e:
            logger.warning(f"Document fetch failed for {rcept_no}: {e}")
            return None
        except Exception as e:
            logger.error(
                f"Document fetch error for {rcept_no}: {e}", exc_info=True
            )
            return None


# ---------------------------------------------------------------------------
# Disclosure processing pipeline
# ---------------------------------------------------------------------------

async def _process_disclosure(item: dict, skip_document: bool = False):
    rcept_no = item.get("rcept_no", "")
    ticker = item.get("stock_code", "") or ""
    corp_name = _clean_text(item.get("corp_name", ""))
    title = _clean_text(item.get("report_nm", "")).strip()

    published_at = datetime.now(timezone.utc)

    # Skip document download for existing items or administrative disclosures
    if skip_document or check_administrative(title):
        raw_text = f"{corp_name} - {title}"
    else:
        raw_text = await _fetch_document_text(rcept_no)
        if raw_text is None:
            raw_text = f"{corp_name} - {title}"
    raw_text = _clean_text(raw_text)

    if not rcept_no:
        logger.warning("Disclosure item missing rcept_no -- skipping")
        return

    supabase = get_supabase()
    existing = (
        supabase.table("disclosures")
        .select("id")
        .eq("dart_rcept_no", rcept_no)
        .execute()
    )
    if existing.data and len(existing.data) > 0:
        logger.debug(f"Disclosure {rcept_no} already exists -- skipping")
        return

    score_result = evaluate_disclosure(
        title=title,
        raw_text=raw_text,
        ticker=ticker,
        supabase=supabase,
    )

    logger.info(
        f"Scored {rcept_no}: {corp_name} - {title[:60]}"
        f" → cat={score_result.category} score={score_result.dvi_score}"
        f" feed_visible={score_result.is_feed_visible}"
        f" skip_llm={score_result.skip_llm}"
        f" risk={score_result.risk_flag or '-'}"
    )

    insert_data = _clean_payload({
        "dart_rcept_no": rcept_no,
        "ticker": ticker,
        "company_name": corp_name,
        "title": title,
        "raw_text": raw_text,
        "published_at": published_at.isoformat(),
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
    })

    if "\\u0000" in json.dumps(insert_data, ensure_ascii=True):
        logger.warning(
            f"Skipping disclosure {rcept_no}: payload still contains null escape"
        )
        return

    try:
        supabase.table("disclosures").insert(insert_data).execute()
        logger.info(
            f"Inserted disclosure {rcept_no}: {corp_name} - {title[:60]}"
            f" (score={score_result.dvi_score}, feed={score_result.is_feed_visible})"
        )
    except Exception as e:
        logger.error(f"Supabase insert failed for {rcept_no}: {e}")
        return

    # LLM enrichment: 80+ full analysis, 60-79 brief summary, <60 skip
    if not score_result.skip_llm:
        brief = score_result.dvi_score < 80
        asyncio.create_task(
            _enrich_with_llm(rcept_no, ticker, corp_name, title, raw_text, brief=brief)
        )


async def _enrich_with_llm(
    rcept_no: str,
    ticker: str,
    corp_name: str,
    title: str,
    raw_text: str,
    brief: bool = False,
):
    try:
        from app.services.groq_llm import analyze_disclosure

        llm_result = await analyze_disclosure(
            ticker=ticker,
            company_name=corp_name,
            title=title,
            raw_text=raw_text,
            brief=brief,
        )

        update_data = _clean_payload({
            "llm_summary": _clean_text(llm_result.llm_summary, limit=8000),
            "key_metrics": [m.model_dump() for m in llm_result.key_metrics],
            "llm_raw_response": llm_result.model_dump(),
            "llm_status": "DONE",
        })

        supabase = get_supabase()
        supabase.table("disclosures").update(update_data).eq(
            "dart_rcept_no", rcept_no
        ).execute()

        logger.info(
            f"LLM enrichment done for {rcept_no}: "
            f"summary_len={len(llm_result.llm_summary)}"
        )

    except Exception as e:
        logger.error(
            f"LLM enrichment failed for {rcept_no}: {e}", exc_info=True
        )
        try:
            supabase = get_supabase()
            supabase.table("disclosures").update({
                "llm_status": "DONE",
                "llm_summary": "LLM 분석 실패",
            }).eq("dart_rcept_no", rcept_no).execute()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Manual trigger
# ---------------------------------------------------------------------------

async def poll_dart_once():
    # Skip polling during DART submission downtime (19:00 ~ 07:30)
    now = datetime.now().astimezone()
    hour = now.hour
    if hour >= 19 or hour < 7:
        logger.debug("Skipping poll during DART downtime (19:00-07:30)")
        return

    logger.info("Polling DART API...")
    items = await _fetch_disclosure_list()

    if not items:
        logger.info("No new disclosures found")
        return

    logger.info(f"Found {len(items)} disclosures -- processing...")

    # Get existing rcept_nos to skip document download
    supabase = get_supabase()
    existing_result = (
        supabase.table("disclosures")
        .select("dart_rcept_no")
        .execute()
    )
    existing_rcept_nos = {row["dart_rcept_no"] for row in (existing_result.data or [])}

    for item in items:
        rcept_no = item.get("rcept_no", "")
        skip_document = rcept_no in existing_rcept_nos
        await _process_disclosure(item, skip_document=skip_document)

    logger.info(f"Poll cycle complete: {len(items)} items processed")
