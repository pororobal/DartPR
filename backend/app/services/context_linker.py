"""
관련공시 파서 & 머저.

Disclosure raw_text 하단 '※ 관련공시' 섹션을 파싱해
Supabase에서 과거 공시를 조회하고, LLM을 통해 통합 분석을 생성한다.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 관련공시 regex
# ---------------------------------------------------------------------------
# DART 문서 하단 형식:
#   ※ 관련공시\t2026-05-14\t투자판단 관련 주요경영사항(CKD-339 승인 신청)
# 연속된 관련공시는 ※ 관련공시가 여러 번 나오거나 \n으로 구분
_RELATED_DISCLOSURE_RE = re.compile(
    r'※\s*관련공시[：:\t]\s*(\d{4}[-\\.]\d{2}[-\\.]\d{2})[：:\t\s]+(.+?)(?=※\s*관련공시|\Z)',
    re.DOTALL,
)

# 한 라인에 여러 관련공시가 탭으로 분리된 경우:
# ※ 관련공시\t날짜\t제목1\n\t\t\t\t\t\t\t\t\t\t\t※관련공시\t날짜\t제목2
_RELATED_LINE_RE = re.compile(
    r'※\s*관련공시\s+(\d{4}[-\\.]\d{2}[-\\.]\d{2})\s+(.+)'
)


@dataclass
class RelatedDisclosure:
    date: str = ""
    title: str = ""
    rcept_no: Optional[str] = None
    raw_text: Optional[str] = None
    llm_summary: Optional[str] = None
    dvi_score: Optional[int] = None
    category: Optional[str] = None


# ---------------------------------------------------------------------------
# Merge prompt
# ---------------------------------------------------------------------------

MERGE_PROMPT = """당신은 DART 공시 분석가입니다.
아래 [현재 공시]의 분석 결과와 [관련공시 이력]을 종합하여
1-2문장 연결 요약 + 전체 방향성/기간을 판단하라.

[현재 공시]
제목: {title}
1차 분석: {summary}
방향성: {sentiment} | 기간: {horizon}

[관련공시 이력]
{timeline}

분석 규칙:
- 요약은 현재 공시와 관련공시의 시간순 흐름(신청→승인, 발행→만기, 진행단계 등)을 중심으로 작성
- 전체 맥락을 고려한 방향성과 영향 기간을 판단
- 공시 원문에 없는 정보, 투자 추천, 주가 예측 절대 금지
- 새 정보를 추가하지 말고 연결 관계만 서술

STRICT OUTPUT — 아래 JSON만 반환:
{{
  "merged_summary": "1-2문장 시간순 흐름 요약",
  "impact_direction": "BENEFICIAL | ADVERSE | NEUTRAL",
  "horizon": "SHORT_TERM | LONG_TERM",
  "confidence": "HIGH | MEDIUM | LOW"
}}"""


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def parse_related_disclosures(raw_text: str) -> list[RelatedDisclosure]:
    """raw_text 하단 '※ 관련공시' 섹션을 파싱한다."""
    if not raw_text or not isinstance(raw_text, str):
        return []

    results: list[RelatedDisclosure] = []
    seen_titles: set[str] = set()

    # 1) 멀티라인 블록 매칭 (※ 관련공시: 날짜 내용)
    for m in _RELATED_DISCLOSURE_RE.finditer(raw_text):
        date = m.group(1).replace(".", "-").replace("\\", "-")
        title = m.group(2).strip()
        # 중복 제거
        key = f"{date}|{title[:50]}"
        if key not in seen_titles:
            seen_titles.add(key)
            results.append(RelatedDisclosure(date=date, title=title))

    # 2) 단일 라인 매칭 (탭 또는 공백으로 구분된 경우)
    if not results:
        for m in _RELATED_LINE_RE.finditer(raw_text):
            date = m.group(1).replace(".", "-").replace("\\", "-")
            title = m.group(2).strip()
            key = f"{date}|{title[:50]}"
            if key not in seen_titles:
                seen_titles.add(key)
                results.append(RelatedDisclosure(date=date, title=title))

    logger.debug(f"Parsed {len(results)} related disclosures from raw_text")
    return results


async def find_in_supabase(
    related: list[RelatedDisclosure],
    ticker: str,
    supabase,
) -> list[RelatedDisclosure]:
    """Supabase에서 동일 ticker + title 유사 매칭으로 관련공시 조회."""
    if not related:
        return related

    for rd in related:
        # title 첫 40자로 ILIKE 검색 (DART 제목이 정확히 일치)
        search_key = rd.title[:40].strip()
        if not search_key:
            continue
        try:
            result = (
                supabase.table("disclosures")
                .select("dart_rcept_no, raw_text, llm_summary, dvi_score, category")
                .eq("ticker", ticker)
                .ilike("title", f"{search_key}%")
                .maybe_single()
                .execute()
            )
            if result.data:
                rd.rcept_no = result.data["dart_rcept_no"]
                rd.raw_text = result.data["raw_text"]
                rd.llm_summary = result.data["llm_summary"]
                rd.dvi_score = result.data["dvi_score"]
                rd.category = result.data["category"]
                logger.debug(f"Found related: {rd.date} {rd.title[:40]} → {rd.rcept_no}")
        except Exception as e:
            logger.debug(f"Supabase lookup failed for '{search_key}': {e}")

    return related


def build_timeline_text(related: list[RelatedDisclosure]) -> str:
    """관련공시 이력을 텍스트로 조립."""
    lines: list[str] = []
    for rd in sorted(related, key=lambda x: x.date):
        info = f"  - {rd.date}"
        if rd.rcept_no:
            info += f" (접수번호: {rd.rcept_no})"
        info += f": {rd.title[:80]}"
        if rd.dvi_score is not None:
            info += f" [DVI {rd.dvi_score}, {rd.category or '-'}]"
        if rd.llm_summary:
            info += f"\n    분석: {rd.llm_summary[:200]}"
        lines.append(info)
    return "\n".join(lines)


def build_merged_prompt(
    title: str,
    summary: str,
    sentiment: str,
    horizon: str,
    related: list[RelatedDisclosure],
) -> str:
    """LLM 통합 분석용 프롬프트 생성."""
    timeline = build_timeline_text([r for r in related if r.rcept_no])
    if not timeline:
        timeline = build_timeline_text(related)  # 제목만이라도 포함

    return MERGE_PROMPT.format(
        title=title[:200],
        summary=summary[:500],
        sentiment=sentiment or "NEUTRAL",
        horizon=horizon or "SHORT_TERM",
        timeline=timeline,
    )
