"""
Backfill script to process pending LLM analyses.

Run this to analyze disclosures that were skipped or failed LLM enrichment.
Usage: python -m scripts.backfill_llm
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.supabase_client import get_supabase
from app.services.groq_llm import analyze_disclosure
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def backfill_pending_llm():
    """Process all disclosures with llm_status=PENDING and score >= 60."""
    supabase = get_supabase()
    
    # Get pending disclosures with score >= 60
    result = (
        supabase.table("disclosures")
        .select("id,dart_rcept_no,ticker,company_name,title,raw_text,dvi_score")
        .eq("llm_status", "PENDING")
        .gte("dvi_score", 60)
        .execute()
    )
    
    rows = result.data or []
    total = len(rows)
    
    if total == 0:
        logger.info("No pending LLM analyses found (score >= 60)")
        return
    
    logger.info(f"Found {total} pending disclosures to process")
    
    processed = 0
    failed = 0
    
    for row in rows:
        rcept_no = row.get("dart_rcept_no", "")
        ticker = row.get("ticker", "")
        corp_name = row.get("company_name", "")
        title = row.get("title", "")
        raw_text = row.get("raw_text", "")
        score = row.get("dvi_score", 0)
        
        logger.info(f"[{processed+1}/{total}] Processing {rcept_no}: {corp_name} - {title[:50]}")
        
        try:
            # Determine brief vs full analysis
            brief = score < 80
            
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
                "dart_rcept_no", rcept_no
            ).execute()
            
            processed += 1
            logger.info(f"  ✓ Completed: summary_len={len(llm_result.llm_summary)}")
            
        except Exception as e:
            failed += 1
            logger.error(f"  ✗ Failed: {e}")
            
            # Mark as DONE with error message to avoid reprocessing
            try:
                supabase.table("disclosures").update({
                    "llm_status": "DONE",
                    "llm_summary": "LLM 분석 실패 (백필)",
                }).eq("dart_rcept_no", rcept_no).execute()
            except Exception:
                pass
    
    logger.info(f"Backfill complete: {processed} succeeded, {failed} failed")


if __name__ == "__main__":
    if not settings.groq_api_key:
        logger.error("GROQ_API_KEY not set in environment")
        sys.exit(1)
    
    asyncio.run(backfill_pending_llm())
