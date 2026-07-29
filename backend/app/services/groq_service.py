"""
Groq LLM service — disclosure analysis via Groq Inference API (free tier).

Two analysis paths:
  - analyze_disclosure:  Full summary + key_metrics for high-impact disclosures.
  - analyze_ambiguity:   Quick sentiment/horizon for ambiguous titles.
"""

import asyncio
import json
import logging
from typing import Any, List

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)
_llm_semaphore = asyncio.Semaphore(2)


_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
_MAX_RETRIES = 3


async def _call_with_retry(client, kwargs: dict) -> Any:
    """Call client.chat.completions.create with exponential backoff on retryable errors."""
    last_exc = None
    for attempt in range(_MAX_RETRIES):
        try:
            return await client.chat.completions.create(**kwargs)
        except Exception as e:
            last_exc = e
            status = None
            if hasattr(e, "status_code"):
                status = e.status_code
            elif hasattr(e, "response") and hasattr(e.response, "status_code"):
                status = e.response.status_code

            if status in _RETRYABLE_STATUSES or status is None:
                if attempt < _MAX_RETRIES - 1:
                    wait = 2 ** attempt + (1 if attempt > 0 else 0)  # 1s, 5s, 9s
                    logger.warning(
                        f"Groq retry {attempt + 1}/{_MAX_RETRIES} after {wait}s "
                        f"(status={status}, err={e})"
                    )
                    await asyncio.sleep(wait)
                    continue
            # Non-retryable or exhausted → surface immediately
            raise
    # All retries exhausted
    raise last_exc  # type: ignore


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

FULL_ANALYSIS_PROMPT = """당신은 DART 공시 원문을 분석해 사실을 명확히 전달하는 증권 정보 분석가입니다.

핵심 원칙: 공시 원문에 적힌 사실만 서술하고, 그 의미를 해석하거나 확장하지 마십시오.
"이 공시가 무엇인지"만 말하고 "이 공시가 어떤 결과를 가져올지"는 말하지 마십시오.

목표: 공시 원문에 기재된 정보를 객관적으로 요약하고, 해당 정보의 성격(일회성/구조적, 단기/장기)을 분류하는 것입니다. 예측이 아니라 분류입니다.

분석 원칙:
1. 반드시 공시 원문에 있는 사실만 서술하십시오. 원문에 없는 정보는 절대 추가하지 마십시오.
2. 핵심 내용을 요약할 때 단순한 사실 나열이 아니라, **공시 원문에 명시된 수치·절차·규정·근거**를 그대로 포함하여 서술하십시오.
3. 이벤트 성격(일회성/구조적)과 영향 기간(단기/장기)은 공시 원문에 기재된 절차와 규정에 근거하여 분류하십시오.
4. 수치가 있다면 반드시 언급하고, 전년 대비 또는 이전 공시 대비 증감도 포함하십시오.
5. key_metrics는 원문에 실제 기재된 핵심 수치만 최대 3개 추출하십시오.

절대 금지 — 위반 시 패널티:
- "매수/매도/투자 추천", "주가 상승/하락 예상"
- 원문에 없는 정보, 시장 루머, 과거 주가 패턴 추측
- "호재/악재/재료/모멘텀" 같은 용어
- "~할 수 있다", "~기여할 전망", "~영향을 미칠 것", "기대된다", "우려된다" 등 예측·인과 표현
- 단순 사실만 나열하고 원문에 기재된 수치·절차·근거는 생략 ("CB를 발행했다"만 쓰고 발행 목적/규모/조건을 쓰지 않는 등)

좋은 예 (기재 금지: 주가 예측·인과 표현 없음):
- "자사주 소각 발표 — 보통주 4,901,094주(발행주식 총수의 3.1%)를 8월 3일 소각 예정. 배당가능이익 범위 내 진행, 자본금 감소 없음. 일회성 이벤트."
- "CB 전환가액을 현 주가 대비 20% 하향 조정(4,500원→3,600원). 전환청구권 행사 시 신주 100만주 발행. 제3자배정 대상은 BBB주식회사."
- "영업외손익으로 흑자전환 — 영업손실 50억, 영업외수익 200억(자산매각)으로 당기순이익 100억 기록. 일회성 요인."
- "최대주주가 A법인에서 B대기업 계열사로 변경(지분율 15%→35%). 변경 사유는 제3자배정 유상증자 참여. 경영권 변동."
- "계약 규모 연 500억(매출액 대비 85%). 계약 상대방은 C기업. 계약 기간 3년. 반복 계약 조항 포함."
- "FDA 임상 3상 중단 발표 — 해당 파이프라인(D코드)의 안전성 문제로 중단. 중단 결정일: 2026-07-27."

나쁜 예 (금지):
- "동사는 CB를 발행했다" (의미 없음. 발행 목적·규모·조건을 포함해야 함)
- "주가가 상승할 것으로 예상된다" (주가 예측 금지)
- "호재다" (레이블링 금지)
- "지분 희석이 발생할 수 있다" (인과 표현 금지)

공시 유형별 공시 원문에 실제 기재된 확인 가능한 정보:
1. 자금조달: 발행 목적(시설/운영/채무상환), 전환가액, 발행 규모, 만기일, 제3자배정 대상.
2. 지배구조: 변경 전·후 최대주주, 지분율 변동, 변경 사유, 변경 일자.
3. 영업계약: 계약 금액(매출액 대비 비중), 계약 상대방, 계약 기간, 반복 계약 조항 유무.
4. 실적: 매출액, 영업이익, 당기순이익 수치 및 증감률, 흑자/적자전환 사유(원문에 기재된 것만).
5. 주주환원: 소각 주식 수, 소각 예정일, 배당가능이익 범위 해당 여부, 자본금 감소 여부.
6. 바이오: 임상 단계, 대상 질환, 대상자 수, 임상 기간, 승인 기관, 승인일.
7. 법적 리스크: 횡령/배임 금액, 상장폐지 사유, 회생절차 신청일(원문에 기재된 것만).
8. 사채 관리: 전환가액 조정 전·후 금액, 조정 사유, 조정일.

key_metrics status 기준 (백엔드 분류 규칙 참고):
- POSITIVE: 자사주 소각, 최초배당, 영업이익 증가, FDA 승인, 기술이전 수취
- NEGATIVE: CB 리픽싱, 적자전환, 자사주 담보, 감사의견 비적정, 횡령
- NEUTRAL: 대표이사 변경, 단순 사채발행 등 명확한 방향성이 없는 경우

STRICT OUTPUT: 아래 JSON 스키마로만 응답하십시오. 마크다운, 설명 텍스트, 코드블록은 절대 금지입니다.
{
  "llm_summary": "String (2-3문장, 공시 원문에 기재된 수치·절차·규정·근거를 포함한 사실 위주 서술. 이벤트 성격(일회성/구조적)과 영향 기간(단기/장기) 분류를 포함.)",
  "key_metrics": [
    {
      "label": "String (예: '전환가액', '계약 금액', '배정 대상')",
      "value": "String",
      "status": "POSITIVE | NEUTRAL | NEGATIVE"
    }
  ]
}"""


BRIEF_ANALYSIS_PROMPT = """당신은 DART 공시 원문을 분석하는 증권 정보 분석가입니다.
공시 원문에 적힌 핵심 사실(수치·절차·규정)을 1-2문장으로 간결히 요약하십시오.
예측·인과 표현("~할 수 있다", "~영향을 미칠 것") 절대 금지. 공시에 기재된 사실만 서술하십시오.
투자 판단, 호재/악재 표현, 주가 영향 예측 절대 금지.

STRICT OUTPUT: 아래 JSON 스키마로만 응답하십시오.
{
  "llm_summary": "1-2문장 핵심 요약 (사실 위주)",
  "key_metrics": []
}"""


AMBIGUITY_ANALYSIS_PROMPT = """당신은 DART 공시 제목과 원문을 분석하는 증권 정보 분석가입니다.

목적: 키워드 매칭만으로는 성격 파악이 어려운 공시의 방향성과 영향 기간을 분류합니다.
예측이 아니라 분류입니다. 공시 원문에 기재된 사실에 근거하여 분류 기준을 적용하십시오.

분석 원칙:
1. 공시 제목과 원문의 사실만으로 판단하십시오. 원문에 없는 정보 절대 금지.
2. 해당 공시 내용의 방향성(수혜/부정/중립)과 영향 기간(단기/장기)을 공시 내용에 기반해 분류하십시오.
3. 확신이 없으면 NEUTRAL로, 불확실하면 confidence LOW로 판단하십시오.
4. "~할 수 있다", "~기대된다", "~우려된다" 같은 예측·인과 표현을 reason에 포함하지 마십시오.
   reason에는 공시 원문에 기재된 사실(이벤트 유형, 금액, 일자 등)만 서술하십시오.

STRICT OUTPUT: 아래 JSON 스키마로만 응답하십시오.
{
  "impact_direction": "BENEFICIAL | ADVERSE | NEUTRAL",
  "horizon": "SHORT_TERM | LONG_TERM",
  "confidence": "HIGH | MEDIUM | LOW",
  "reason": "1-2문장 (공시 원문 사실 기반. 예측·인과 표현 금지.)"
}"""


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class KeyMetricItem(BaseModel):
    label: str
    value: str
    status: str


class GroqSummaryOutput(BaseModel):
    llm_summary: str = ""
    key_metrics: List[KeyMetricItem] = Field(default_factory=list)


class GroqAmbiguityOutput(BaseModel):
    impact_direction: str = "NEUTRAL"
    horizon: str = "SHORT_TERM"
    confidence: str = "LOW"
    reason: str = ""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_summary_fallback(error_msg: str) -> GroqSummaryOutput:
    logger.warning(f"Groq summary fallback: {error_msg}")
    return GroqSummaryOutput(llm_summary="LLM 분석 실패", key_metrics=[])


def _safe_ambiguity_fallback(error_msg: str) -> GroqAmbiguityOutput:
    logger.warning(f"Groq ambiguity fallback: {error_msg}")
    return GroqAmbiguityOutput(impact_direction="NEUTRAL", confidence="LOW", reason="LLM 분석 실패")


def _client() -> AsyncOpenAI | None:
    """Return an OpenAI-compatible client pointing to Groq."""
    if not settings.groq_api_key:
        return None
    return AsyncOpenAI(api_key=settings.groq_api_key, base_url=settings.groq_base_url)


def _build_user_message(ticker: str, company_name: str, title: str, raw_text: str) -> str:
    return f"""종목코드: {ticker}
회사명: {company_name}
공시제목: {title}

공시 원문:
{raw_text[:3500]}
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def analyze_disclosure(
    ticker: str,
    company_name: str,
    title: str,
    raw_text: str,
    brief: bool = False,
) -> GroqSummaryOutput:
    """Full summary + key_metrics extraction. Uses groq_model (high-quality)."""
    client = _client()
    if client is None:
        logger.warning("GROQ_API_KEY not set -- skipping analysis")
        return _safe_summary_fallback("GROQ_API_KEY not configured")

    model = settings.groq_model
    system_prompt = BRIEF_ANALYSIS_PROMPT if brief else FULL_ANALYSIS_PROMPT
    max_tokens = 120 if brief else 800

    try:
        kwargs = dict(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": _build_user_message(ticker, company_name, title, raw_text)},
            ],
            temperature=0.1,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )

        async with _llm_semaphore:
            response = await _call_with_retry(client, kwargs)

        content = response.choices[0].message.content
        if not content:
            return _safe_summary_fallback("Empty Groq response")

        parsed = json.loads(content)
        return GroqSummaryOutput(
            llm_summary=parsed.get("llm_summary", ""),
            key_metrics=[KeyMetricItem(**m) for m in parsed.get("key_metrics", [])],
        )

    except json.JSONDecodeError as e:
        return _safe_summary_fallback(f"JSON parse error: {e}")
    except ImportError:
        logger.warning("openai package not installed")
        return _safe_summary_fallback("openai package not installed")
    except Exception as e:
        logger.error(f"Groq analysis call failed after retries: {e}", exc_info=True)
        return _safe_summary_fallback(f"Groq API error: {e}")


async def analyze_ambiguity(
    ticker: str,
    company_name: str,
    title: str,
    raw_text: str,
) -> GroqAmbiguityOutput:
    """Quick sentiment/horizon classification. Uses groq_ambiguity_model (lightweight)."""
    client = _client()
    if client is None:
        logger.warning("GROQ_API_KEY not set -- skipping ambiguity analysis")
        return _safe_ambiguity_fallback("GROQ_API_KEY not configured")

    model = settings.groq_ambiguity_model

    try:
        kwargs = dict(
            model=model,
            messages=[
                {"role": "system", "content": AMBIGUITY_ANALYSIS_PROMPT},
                {"role": "user", "content": _build_user_message(ticker, company_name, title, raw_text)},
            ],
            temperature=0.1,
            max_tokens=300,
            response_format={"type": "json_object"},
        )

        async with _llm_semaphore:
            response = await _call_with_retry(client, kwargs)

        content = response.choices[0].message.content
        if not content:
            return _safe_ambiguity_fallback("Empty Groq response")

        parsed = json.loads(content)
        return GroqAmbiguityOutput(
            impact_direction=parsed.get("impact_direction", "NEUTRAL"),
            horizon=parsed.get("horizon", "SHORT_TERM"),
            confidence=parsed.get("confidence", "LOW"),
            reason=parsed.get("reason", ""),
        )

    except json.JSONDecodeError as e:
        return _safe_ambiguity_fallback(f"JSON parse error: {e}")
    except ImportError:
        logger.warning("openai package not installed")
        return _safe_ambiguity_fallback("openai package not installed")
    except Exception as e:
        logger.error(f"Groq ambiguity call failed after retries: {e}", exc_info=True)
        return _safe_ambiguity_fallback(f"Groq API error: {e}")
