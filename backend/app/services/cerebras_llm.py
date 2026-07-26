"""
Cerebras LLM service — disclosure analysis via Cerebras Inference API.
"""

import asyncio
import json
import logging
from typing import List, Optional

from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)
_cerebras_semaphore = asyncio.Semaphore(2)


ANALYSIS_SYSTEM_PROMPT = """당신은 DART 공시 원문을 분석하는 증권사 애널리스트입니다.
투자자에게 진짜 유용한 인사이트를 제공하는 것이 목표입니다.

원칙:
1. 공시 원문에 있는 사실만으로 분석하십시오. 원문에 없는 정보는 절대 추가하지 마십시오.
2. 핵심 내용을 요약할 때 단순한 사실 나열이 아니라, **그 사실이 투자자에게 어떤 의미인지**를 1-2문장으로 설명하십시오.
3. 수치가 있다면 반드시 언급하고, 전년 대비 또는 이전 공시 대비 증감도 포함하십시오.
4. key_metrics는 원문에 실제 기재된 핵심 수치만 최대 3개 추출하십시오.

절대 금지:
- "매수/매도/투자 추천", "주가 상승/하락 예상" → 투자 판단 금지
- 원문에 없는 정보, 시장 루머, 과거 주가 패턴 추측
- "호재/악재/재료/모멘텀" 같은 용어 사용

좋은 예:
- "자사주를 취득해 소각하는 것은 발행주식 총수를 줄여 주당 가치를 높이는 효과"
- "운영자금 목적의 CB 발행은 이자 부담 없이 자금을 조달하나, 향후 전환 시 희석 우려"
- "계약 규모가 최근 매출액 대비 85%로, 실적에 미치는 영향이 큰 대규모 계약"

STRICT OUTPUT: 아래 JSON 스키마로만 응답하십시오.
{
  "llm_summary": "String (2-3문장, 핵심 사실 + 그 사실이 투자자에게 갖는 의미)",
  "key_metrics": [
    {
      "label": "String",
      "value": "String",
      "status": "POSITIVE | NEUTRAL | NEGATIVE"
    }
  ]
}"""


BRIEF_ANALYSIS_PROMPT = """당신은 DART 공시 원문을 분석하는 증권사 애널리스트입니다.
공시 원문을 읽고 핵심 사실을 1-2문장으로 간결히 요약하십시오.
투자 판단, 호재/악재 표현, 주가 영향 예측 절대 금지.

STRICT OUTPUT: 아래 JSON 스키마로만 응답하십시오.
{
  "llm_summary": "1-2문장 핵심 요약",
  "key_metrics": []
}"""


AMBIGUITY_SYSTEM_PROMPT = """당신은 DART 공시 제목과 원문을 분석하는 증권 전문가입니다.

목적: 키워드 매칭만으로는 호재/악재 판단이 어려운 공시의 실제 성격을 분석합니다.

분석 원칙:
1. 공시 제목과 원문의 사실만으로 판단하십시오.
2. 해당 공시가 주가에 미칠 영향의 방향성(긍정/부정/중립)과 시간 범위(단기/장기)를 판단하십시오.
3. 확신이 없으면 NEUTRAL로 판단하십시오.

STRICT OUTPUT: 아래 JSON 스키마로만 응답하십시오.
{
  "sentiment": "POSITIVE | NEGATIVE | NEUTRAL",
  "horizon": "SHORT_TERM | LONG_TERM",
  "confidence": "HIGH | MEDIUM | LOW",
  "reason": "1-2문장 요약 (판단 근거)"
}"""


class KeyMetricItem(BaseModel):
    label: str
    value: str
    status: str


class CerebrasAnalysisOutput(BaseModel):
    llm_summary: str = ""
    key_metrics: List[KeyMetricItem] = Field(default_factory=list)


class CerebrasAmbiguityOutput(BaseModel):
    sentiment: str = "NEUTRAL"
    horizon: str = "SHORT_TERM"
    confidence: str = "LOW"
    reason: str = ""


def _safe_analysis_fallback(error_msg: str) -> CerebrasAnalysisOutput:
    logger.warning(f"Cerebras analysis fallback: {error_msg}")
    return CerebrasAnalysisOutput(llm_summary="LLM 분석 실패", key_metrics=[])


def _safe_ambiguity_fallback(error_msg: str) -> CerebrasAmbiguityOutput:
    logger.warning(f"Cerebras ambiguity fallback: {error_msg}")
    return CerebrasAmbiguityOutput(sentiment="NEUTRAL", confidence="LOW", reason="LLM 분석 실패")


def _build_user_message(ticker: str, company_name: str, title: str, raw_text: str) -> str:
    return f"""종목코드: {ticker}
회사명: {company_name}
공시제목: {title}

공시 원문:
{raw_text[:3500]}
"""


async def analyze_disclosure(
    ticker: str,
    company_name: str,
    title: str,
    raw_text: str,
    brief: bool = False,
) -> CerebrasAnalysisOutput:
    if not settings.cerebras_api_key:
        logger.warning("CEREBRAS_API_KEY not set -- skipping analysis")
        return _safe_analysis_fallback("CEREBRAS_API_KEY not configured")

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=settings.cerebras_api_key,
            base_url=settings.cerebras_base_url,
        )

        system_prompt = BRIEF_ANALYSIS_PROMPT if brief else ANALYSIS_SYSTEM_PROMPT
        max_tokens = 150 if brief else 700

        async with _cerebras_semaphore:
            response = await client.chat.completions.create(
                model=settings.cerebras_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": _build_user_message(ticker, company_name, title, raw_text)},
                ],
                temperature=0.1,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )

        content = response.choices[0].message.content
        if not content:
            return _safe_analysis_fallback("Empty Cerebras response")

        parsed = json.loads(content)
        return CerebrasAnalysisOutput(
            llm_summary=parsed.get("llm_summary", ""),
            key_metrics=[KeyMetricItem(**m) for m in parsed.get("key_metrics", [])],
        )

    except json.JSONDecodeError as e:
        return _safe_analysis_fallback(f"JSON parse error: {e}")
    except ImportError:
        logger.warning("openai package not installed -- skipping Cerebras")
        return _safe_analysis_fallback("openai package not installed")
    except Exception as e:
        logger.error(f"Cerebras analysis call failed: {e}", exc_info=True)
        return _safe_analysis_fallback(f"Cerebras API error: {e}")


async def analyze_ambiguity(
    ticker: str,
    company_name: str,
    title: str,
    raw_text: str,
) -> CerebrasAmbiguityOutput:
    if not settings.cerebras_api_key:
        logger.warning("CEREBRAS_API_KEY not set -- skipping ambiguity analysis")
        return _safe_ambiguity_fallback("CEREBRAS_API_KEY not configured")

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=settings.cerebras_api_key,
            base_url=settings.cerebras_base_url,
        )

        async with _cerebras_semaphore:
            response = await client.chat.completions.create(
                model=settings.cerebras_model,
                messages=[
                    {"role": "system", "content": AMBIGUITY_SYSTEM_PROMPT},
                    {"role": "user", "content": _build_user_message(ticker, company_name, title, raw_text)},
                ],
                temperature=0.1,
                max_tokens=200,
                response_format={"type": "json_object"},
            )

        content = response.choices[0].message.content
        if not content:
            return _safe_ambiguity_fallback("Empty Cerebras response")

        parsed = json.loads(content)
        return CerebrasAmbiguityOutput(
            sentiment=parsed.get("sentiment", "NEUTRAL"),
            horizon=parsed.get("horizon", "SHORT_TERM"),
            confidence=parsed.get("confidence", "LOW"),
            reason=parsed.get("reason", ""),
        )

    except json.JSONDecodeError as e:
        return _safe_ambiguity_fallback(f"JSON parse error: {e}")
    except ImportError:
        logger.warning("openai package not installed -- skipping Cerebras")
        return _safe_ambiguity_fallback("openai package not installed")
    except Exception as e:
        logger.error(f"Cerebras ambiguity call failed: {e}", exc_info=True)
        return _safe_ambiguity_fallback(f"Cerebras API error: {e}")
