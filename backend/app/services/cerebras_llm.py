"""
Cerebras LLM service — ambiguous disclosure sentiment classification.

Called when keyword matching alone is insufficient to determine whether
a disclosure is positive or negative (e.g. 신규시설 투자, 풍문 해명, 증권신고서).
"""

import asyncio
import json
import logging
from typing import Optional

from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)
_cerebras_semaphore = asyncio.Semaphore(2)


SYSTEM_PROMPT = """당신은 DART 공시 제목과 원문을 분석하는 증권 전문가입니다.

목적: 키워드 매칭만으로는 호재/악재 판단이 어려운 공시의 실제 성격을 분석합니다.

분석 대상 (애매한 공시 예시):
- 신규시설 투자 / 시설투자 → 성장 투자(긍정) vs 자금 부담(부정) 여부 판단
- 풍문또는보도에 대한 해명 → 풍문 확인(긍정/부정) vs 부인(중립) 여부
- 증권신고서 / 투자설명서 → 조달 규모와 목적에 따라 긍정/부정/중립
- 채무보증 / 담보제공 → 리스크 정도에 따라 부정/중립
- 대표이사 변경 → 새 경영진 기대(긍정) vs 불안정(부정)
- 지배구조 보고 → 단순 공시(중립) vs 리스크 시사(부정)
- 소액공모 / 일괄신고 → 자금조달 규모와 목적에 따라 판단
- 자율공시 → 경영 자신감(긍정) vs 방어적 공시(부정)

분석 원칙:
1. 공시 제목과 원문의 사실만으로 판단하십시오.
2. 해당 공시가 주가에 미칠 영향의 방향성(긍정/부정/중립)과 시간 범위(단기/장기)를 판단하십시오.
3. 확신이 없으면 NEUTRAL로 판단하십시오.
4. 원문에 없는 정보는 절대 추가하지 마십시오.

STRICT OUTPUT: 아래 JSON 스키마로만 응답하십시오. 마크다운, 설명 텍스트, 코드블록은 절대 금지입니다.

{
  "sentiment": "POSITIVE | NEGATIVE | NEUTRAL",
  "horizon": "SHORT_TERM | LONG_TERM",
  "confidence": "HIGH | MEDIUM | LOW",
  "reason": "1-2문장 요약 (판단 근거)"
}"""


class CerebrasOutput(BaseModel):
    sentiment: str = "NEUTRAL"
    horizon: str = "SHORT_TERM"
    confidence: str = "LOW"
    reason: str = ""


def _safe_fallback(error_msg: str) -> CerebrasOutput:
    logger.warning(f"Cerebras LLM fallback: {error_msg}")
    return CerebrasOutput(sentiment="NEUTRAL", confidence="LOW", reason="LLM 분석 실패")


async def analyze_ambiguity(
    ticker: str,
    company_name: str,
    title: str,
    raw_text: str,
) -> CerebrasOutput:
    if not settings.cerebras_api_key:
        logger.warning("CEREBRAS_API_KEY not set -- skipping ambiguity analysis")
        return _safe_fallback("CEREBRAS_API_KEY not configured")

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=settings.cerebras_api_key,
            base_url=settings.cerebras_base_url,
        )

        user_message = f"""종목코드: {ticker}
회사명: {company_name}
공시제목: {title}

공시 원문:
{raw_text[:2500]}
"""

        async with _cerebras_semaphore:
            response = await client.chat.completions.create(
                model=settings.cerebras_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.1,
                max_tokens=200,
                response_format={"type": "json_object"},
            )

        content = response.choices[0].message.content
        if not content:
            return _safe_fallback("Empty Cerebras response")

        parsed = json.loads(content)
        return CerebrasOutput(
            sentiment=parsed.get("sentiment", "NEUTRAL"),
            horizon=parsed.get("horizon", "SHORT_TERM"),
            confidence=parsed.get("confidence", "LOW"),
            reason=parsed.get("reason", ""),
        )

    except json.JSONDecodeError as e:
        return _safe_fallback(f"JSON parse error: {e}")
    except ImportError:
        logger.warning("openai package not installed -- skipping Cerebras")
        return _safe_fallback("openai package not installed")
    except Exception as e:
        logger.error(f"Cerebras LLM call failed: {e}", exc_info=True)
        return _safe_fallback(f"Cerebras API error: {e}")
