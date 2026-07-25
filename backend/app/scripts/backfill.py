"""
Backfill script: fetch past disclosures from OpenDART, score, and optionally
run LLM enrichment on high-scoring items.

Usage:
    python -m app.scripts.backfill fetch [--days 90] [--date YYYYMMDD]
    python -m app.scripts.backfill llm   [--limit 50]

Commands:
    fetch   Fetch + score past disclosures from OpenDART and insert into DB.
            Resumes automatically by skipping existing dart_rcept_no values.
            Iterates day-by-day, respecting OpenDART rate limits.

    llm     LLM-enrich existing disclosures with score >= 80 that have no
            llm_summary yet. Uses 1 req/sec to respect Groq Free Tier (30 RPM).
"""

import asyncio
import json
import logging
import zipfile
import unicodedata
import re
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Optional

import httpx

from app.config import settings
from app.services.supabase_client import get_supabase
from app.services.rules_engine import (
    check_administrative,
    evaluate_disclosure,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("backfill")


# ─── helpers ───────────────────────────────────────────────────────

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
_TAG_RE = re.compile(r"<[^>]+>")


def _clean_text(value: object, limit: int = 50000) -> str:
    if value is None:
        return ""
    text = str(value)
    text = unicodedata.normalize("NFC", text)
    text = text.encode("utf-8", errors="replace").decode("utf-8")
    text = _CONTROL_CHAR_RE.sub(" ", text)
    return text[:limit]


def _decode_bytes(data: bytes) -> str:
    for encoding in ("utf-8", "cp949", "euc-kr"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _strip_markup(text: str) -> str:
    return _TAG_RE.sub(" ", text)


# ─── OpenDART API ──────────────────────────────────────────────────

OPENDART_LIST_URL = "https://opendart.fss.or.kr/api/list.json"
OPENDART_DOCUMENT_URL = "https://opendart.fss.or.kr/api/document.xml"


MAX_PAGES_PER_DAY = 30  # Safety limit: at most 30 pages (3000 items) per day

async def _fetch_list_for_date(date_str: str) -> list[dict]:
    all_items: list[dict] = []
    page_no = 1
    page_count = 100
    seen_rcept_nos: set[str] = set()
    seen_content_keys: set[tuple[str, str]] = set()  # (corp_name, report_nm) dedup

    async with httpx.AsyncClient(timeout=30.0) as client:
        while page_no <= MAX_PAGES_PER_DAY:
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
                logger.error(f"HTTP error for {date_str} page {page_no}: {e}")
                break
            except Exception as e:
                logger.error(f"Fetch error for {date_str} page {page_no}: {e}")
                break

            if data.get("status") != "000":
                logger.warning(f"API error for {date_str}: {data.get('message', 'unknown')}")
                if page_no == 1:
                    return []
                break

            items = data.get("list", [])
            if not items:
                break

            # Safety: detect duplicate pages (API returning same data in loop)
            page_rcept_nos = {i.get("rcept_no", "") for i in items}
            if page_rcept_nos.issubset(seen_rcept_nos):
                logger.info(f"{date_str} page {page_no}: all rcept_no already seen — stopping")
                break

            # Content-based dedup: OpenDART may return same filing with different rcept_no
            deduped = []
            for item in items:
                content_key = (item.get("corp_name", ""), item.get("report_nm", ""))
                if content_key not in seen_content_keys:
                    seen_content_keys.add(content_key)
                    deduped.append(item)

            if not deduped:
                logger.info(f"{date_str} page {page_no}: all content already seen — stopping")
                break

            all_items.extend(deduped)
            seen_rcept_nos.update(page_rcept_nos)

            if len(items) < page_count:
                break

            page_no += 1
            await asyncio.sleep(1)

    return all_items


async def _fetch_document_text(rcept_no: str) -> Optional[str]:
    params = {"crtfc_key": settings.opendart_api_key, "rcept_no": rcept_no}
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
                content = content.replace(b"\x00", b"")
                if content.strip():
                    return _strip_markup(_decode_bytes(content))
                return None

            return _strip_markup(_decode_bytes(content))
        except httpx.HTTPError as e:
            logger.warning(f"Document fetch failed for {rcept_no}: {e}")
            return None
        except Exception as e:
            logger.error(f"Document fetch error for {rcept_no}: {e}")
            return None


# ─── DB helpers ────────────────────────────────────────────────────

def _get_existing_rcept_nos(supabase) -> set[str]:
    """Load ALL existing dart_rcept_no values with pagination (up to 100k)."""
    existing: set[str] = set()
    start = 0
    page_size = 5000
    while True:
        result = supabase.table("disclosures").select("dart_rcept_no").range(start, start + page_size - 1).execute()
        rows = result.data or []
        if not rows:
            break
        existing.update(row["dart_rcept_no"] for row in rows)
        if len(rows) < page_size:
            break
        start += page_size
    return existing


# ─── Process single disclosure (local only, no API calls) ──────────

def _score_item(item: dict) -> Optional[dict]:
    """Score a single disclosure item locally. Returns insert_data or None."""
    rcept_no = item.get("rcept_no", "")
    ticker = item.get("stock_code", "") or ""
    corp_name = _clean_text(item.get("corp_name", ""))
    title = _clean_text(item.get("report_nm", "")).strip()
    published_at_str = item.get("rcept_dt", "")

    if not rcept_no:
        return None

    # Use title-only for scoring (skip document download)
    raw_text = f"{corp_name} - {title}"
    raw_text = _clean_text(raw_text)

    try:
        published_at = datetime.strptime(published_at_str, "%Y%m%d").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        published_at = datetime.now(timezone.utc)

    supabase_singleton = get_supabase()
    score_result = evaluate_disclosure(
        title=title,
        raw_text=raw_text,
        ticker=ticker,
        supabase=supabase_singleton,
    )

    insert_data = {
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
    }

    if "\\u0000" in json.dumps(insert_data, ensure_ascii=True):
        logger.warning(f"Skipping {rcept_no}: still contains null escape")
        return None

    return insert_data


# ─── Commands ──────────────────────────────────────────────────────

async def cmd_fetch(days: int = 90, start_date_str: str = ""):
    """Fetch + score past N days of disclosures from OpenDART (bulk, fast)."""
    if not settings.opendart_api_key:
        logger.error("OPENDART_API_KEY not set")
        return

    supabase = get_supabase()
    existing = _get_existing_rcept_nos(supabase)
    logger.info(f"Found {len(existing)} existing records in DB")

    if start_date_str:
        start_date = datetime.strptime(start_date_str, "%Y%m%d").replace(tzinfo=timezone.utc)
    else:
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

    end_date = datetime.now(timezone.utc)
    total_new = 0
    total_skipped = 0
    total_errors = 0

    current = start_date
    while current <= end_date:
        date_str = current.strftime("%Y%m%d")
        weekday = current.weekday()
        current += timedelta(days=1)

        # Skip weekends
        if weekday >= 5:
            continue

        items = await _fetch_list_for_date(date_str)
        if not items:
            logger.info(f"{date_str}: 0 disclosures")
            continue

        new_items = [i for i in items if i.get("rcept_no", "") not in existing]
        skipped = len(items) - len(new_items)
        total_skipped += skipped

        if not new_items:
            if skipped:
                logger.info(f"{date_str}: {len(items)} total, all {skipped} already exist")
            continue

        # Score all new items locally (no API calls, no sleep)
        batch = []
        for item in new_items:
            data = _score_item(item)
            if data:
                batch.append(data)

        if not batch:
            logger.info(f"{date_str}: {len(new_items)} new items, 0 scored")
            continue

        # Bulk insert
        try:
            supabase.table("disclosures").insert(batch).execute()
            for data in batch:
                existing.add(data["dart_rcept_no"])
            total_new += len(batch)
            logger.info(
                f"{date_str}: {len(items)} total, {len(batch)} inserted, "
                f"{skipped} skipped ({total_new} cumulative)"
            )
        except Exception as e:
            # Fallback: insert one by one
            logger.warning(f"{date_str}: bulk insert failed ({e}), falling back")
            for data in batch:
                try:
                    supabase.table("disclosures").insert(data).execute()
                    existing.add(data["dart_rcept_no"])
                    total_new += 1
                except Exception as e2:
                    logger.error(f"  insert {data['dart_rcept_no']} failed: {e2}")
                    total_errors += 1

        # Small delay between days (not per-item)
        await asyncio.sleep(1)

    logger.info(
        f"Fetch complete. Total: {total_new} inserted, "
        f"{total_skipped} skipped, {total_errors} errors"
    )


async def cmd_llm(limit: int = 50):
    """LLM-enrich existing disclosures with score >= 80 and no summary."""
    if not settings.groq_api_key:
        logger.error("GROQ_API_KEY not set")
        return

    supabase = get_supabase()
    result = (
        supabase.table("disclosures")
        .select("*")
        .gte("dvi_score", 80)
        .is_("llm_summary", "null")
        .order("dvi_score", desc=True)
        .limit(limit)
        .execute()
    )
    rows = result.data or []
    logger.info(f"Found {len(rows)} disclosures needing LLM enrichment")

    if not rows:
        return

    from app.services.groq_llm import analyze_disclosure

    done = 0
    for row in rows:
        rcept_no = row.get("dart_rcept_no", "")
        brief = (row.get("dvi_score", 0) or 0) < 80

        llm_result = await analyze_disclosure(
            ticker=row.get("ticker", ""),
            company_name=row.get("company_name", ""),
            title=row.get("title", ""),
            raw_text=row.get("raw_text", ""),
            brief=brief,
        )

        update_data = {
            "llm_summary": llm_result.llm_summary,
            "key_metrics": [m.model_dump() for m in llm_result.key_metrics],
            "llm_raw_response": llm_result.model_dump(),
            "llm_status": "DONE",
        }

        try:
            supabase.table("disclosures").update(update_data).eq(
                "dart_rcept_no", rcept_no
            ).execute()
            logger.info(
                f"LLM enriched {rcept_no}: {row.get('company_name','')} "
                f"score={row.get('dvi_score')}"
            )
            done += 1
        except Exception as e:
            logger.error(f"LLM update failed for {rcept_no}: {e}")

        # Groq Free Tier: 30 req/min → 1 req per 2+ seconds
        await asyncio.sleep(2.5)

    logger.info(f"LLM enrichment complete: {done}/{len(rows)} done")


# ─── Entry point ───────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="DART backfill script")
    sub = parser.add_subparsers(dest="command", required=True)

    fetch_parser = sub.add_parser("fetch", help="Fetch + score past disclosures")
    fetch_parser.add_argument(
        "--days", type=int, default=90, help="Days to look back (default: 90)"
    )
    fetch_parser.add_argument(
        "--date", type=str, default="", help="Start date YYYYMMDD (overrides --days)"
    )

    llm_parser = sub.add_parser("llm", help="LLM-enrich missing disclosures")
    llm_parser.add_argument(
        "--limit", type=int, default=50, help="Max disclosures to process (default: 50)"
    )

    args = parser.parse_args()

    if args.command == "fetch":
        asyncio.run(cmd_fetch(days=args.days, start_date_str=args.date))
    elif args.command == "llm":
        asyncio.run(cmd_llm(limit=args.limit))
