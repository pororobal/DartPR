"""
Cerebras LLM service — disclosure analysis via Cerebras Inference API.
"""

import asyncio
import json
import logging
from typing import List, Optional

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)
_llm_semaphore = asyncio.Semaphore(2)


ANALYSIS_SYSTEM_PROMPT = """당신은 DART 공시 원문을 분석해 사실을 명확히 전달하는 증권 정보 분석가입니다.
목표: 공시 원문에 기재된 정보를 객관적으로 요약하고, 해당 정보의 성격(일회성/구조적, 단기/장기)을 설명하는 것입니다.

원칙:
1. 공시 원문에 있는 사실만으로 분석하십시오. 원문에 없는 정보는 절대 추가하지 마십시오.
2. 핵심 내용을 요약할 때 단순한 사실 나열이 아니라, **그 사실의 성격과 시사점**을 1-2문장으로 설명하십시오.
   - 해당 사항이 일회성 이벤트인지, 구조적 변화인지 구분하십시오.
   - 단기적 영향인지, 장기적 영향인지 구분하십시오.
3. 수치가 있다면 반드시 언급하고, 전년 대비 또는 이전 공시 대비 증감도 포함하십시오.
4. key_metrics는 원문에 실제 기재된 핵심 수치만 최대 3개 추출하십시오.

절대 금지:
- "매수/매도/투자 추천", "주가 상승/하락 예상" → 투자 판단 금지
- 원문에 없는 정보, 시장 루머, 과거 주가 패턴 추측
- "호재/악재/재료/모멘텀" 같은 용어 사용
- 단순 사실만 나열하고 의미 해석 생략

좋은 예:
- "자사주 소각 발표 — 발행주식 수가 줄어 기존 주주의 지분 가치가 높아지는 효과. 일회성 이벤트로 단기보다 장기적 영향"
- "CB 전환가액을 현 주가 대비 20% 낮게 리픽싱 — 전환청구가 발생하면 신주 발행으로 지분 희석이 발생할 수 있음"
- "영업외손익으로 흑자전환 — 영업이익이 아닌 일회성 요인에 의한 흑자로, 실질적 수익성 개선으로 보기 어려움"
- "최대주주가 대기업 계열사로 변경 — 재무적 안정성 및 사업 시너지가 기대되는 구조적 변화"
- "계약 규모가 연매출 대비 85% — 실적에 큰 영향을 줄 수 있는 대규모 계약. 향후 매출 인식 시점이 중요"
- "FDA 임상 3상 중단 발표 — 해당 파이프라인의 상업화 가능성이 낮아져 기대 가치가 하락"

나쁜 예 (금지):
- "동사는 CB를 발행했다" (의미 없음. 왜, 어떤 영향인지까지 서술해야 함)
- "주가가 상승할 것으로 예상된다" (주가 예측 금지)
- "호재다" (레이블링 금지)

공시 유형별 분석 참고 맥락:
1. 자금조달: CB 발행 목적(시설/운영/채무상환)과 전환가액이 핵심. 리픽싱은 기존 주주 지분 희석 가능성. 운영자금 목적은 통상적.
2. 지배구조: 최대주주 변경 시 인수 주체의 성격이 핵심. 대기업 계열사 편입은 장기적 사업 변화 가능성.
3. 영업계약: 계약 규모(매출액 대비 비중)와 상대방 신뢰도가 중요. 대규모 계약은 단기 실적 변수. 반복 계약 여부가 장기 관점.
4. 실적: 흑자전환의 질(영업 vs 영업외)과 적자전환의 일회성 여부 구분 필수. 추세 전환인지, 일시적 요인인지 판단.
5. 주주환원: 자사주 소각→지분 가치 상승 구조. 자사주 담보 제공→재무적 부담 가능성.
6. 바이오: FDA 승인/임상 결과는 해당 파이프라인의 상업화 가능성과 직결. 규모 미공개 계약은 불확실성 존재.
7. 법적 리스크: 횡령/배임/상장폐지/회생은 기업 펀더멘탈에 중대한 영향을 미치는 이벤트.
8. 사채 관리: 전환가액 조정 방향성(상향/하향)이 핵심. 전환청구권 행사 시 신주 발행으로 지분 변동 발생.

key_metrics status 기준:
- POSITIVE: 자사주 소각, 최초배당, 영업이익 증가, FDA 승인, 기술이전 수취
- NEGATIVE: CB 리픽싱, 적자전환, 자사주 담보, 감사의견 비적정, 횡령
- NEUTRAL: 대표이사 변경, 단순 사채발행 등 명확한 방향성이 없는 경우

STRICT OUTPUT: 아래 JSON 스키마로만 응답하십시오. 마크다운, 설명 텍스트, 코드블록은 절대 금지입니다.
{
  "llm_summary": "String (2-3문장, 핵심 사실 + 시사점 + 단기/장기 성격)",
  "key_metrics": [
    {
      "label": "String (예: '전환가액', '계약 금액', '배정 대상')",
      "value": "String",
      "status": "POSITIVE | NEUTRAL | NEGATIVE"
    }
  ]
}"""


BRIEF_ANALYSIS_PROMPT = """당신은 DART 공시 원문을 분석하는 증권사 애널리스트입니다.
공시 원문을 읽고 핵심 사실을 1-2문장으로 간결히 요약하십시오.
단순 사실 나열이 아니라, 그 사실이 투자자에게 갖는 의미를 포함하십시오.
투자 판단, 호재/악재 표현, 주가 영향 예측 절대 금지.

STRICT OUTPUT: 아래 JSON 스키마로만 응답하십시오.
{
  "llm_summary": "1-2문장 핵심 요약",
  "key_metrics": []
}"""


AMBIGUITY_SYSTEM_PROMPT = """당신은 DART 공시 제목과 원문을 분석하는 증권 정보 분석가입니다.

목적: 키워드 매칭만으로는 성격 파악이 어려운 공시를 분석합니다.

분석 원칙:
1. 공시 제목과 원문의 사실만으로 판단하십시오. 원문에 없는 정보 절대 금지.
2. 해당 공시 내용의 방향성(수혜/부정/중립)과 영향 기간(단기/장기)을 공시 내용에 기반해 판단하십시오.
3. 확신이 없으면 NEUTRAL로, 불확실하면 confidence LOW로 판단하십시오.

좋은 예:
- "CB 전환가액을 현 주가보다 낮게 하향 조정 → 신주 발행 시 지분 희석 발생, 전환청구 가능성 높아짐" → ADVERSE / SHORT_TERM / HIGH
- "자회사 지분 100% 추가 취득 → 연결 강화로 장기 수익성 개선 구조, 인수 금액 대비 자금 부담은 제한적" → BENEFICIAL / LONG_TERM / MEDIUM
- "타법인 주식 50억 취득(자기자본 3%) → 소규모 지분 투자, 전략적 목적이 확인될 때까지 추가 정보 필요" → NEUTRAL / SHORT_TERM / LOW

STRICT OUTPUT: 아래 JSON 스키마로만 응답하십시오.
{
  "impact_direction": "BENEFICIAL | ADVERSE | NEUTRAL",
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
    impact_direction: str = "NEUTRAL"
    horizon: str = "SHORT_TERM"
    confidence: str = "LOW"
    reason: str = ""


def _safe_analysis_fallback(error_msg: str) -> CerebrasAnalysisOutput:
    logger.warning(f"LLM analysis fallback: {error_msg}")
    return CerebrasAnalysisOutput(llm_summary="LLM 분석 실패", key_metrics=[])


def _safe_ambiguity_fallback(error_msg: str) -> CerebrasAmbiguityOutput:
    logger.warning(f"LLM ambiguity fallback: {error_msg}")
    return CerebrasAmbiguityOutput(impact_direction="NEUTRAL", confidence="LOW", reason="LLM 분석 실패")


def _pick_llm_client() -> AsyncOpenAI | None:
    """Return an OpenAI-compatible client — prefers Groq (free) over Cerebras (paid)."""
    if settings.groq_api_key:
        return AsyncOpenAI(api_key=settings.groq_api_key, base_url=settings.groq_base_url)
    if settings.cerebras_api_key:
        logger.info("Groq key not set, falling back to Cerebras (requires billing)")
        return AsyncOpenAI(api_key=settings.cerebras_api_key, base_url=settings.cerebras_base_url)
    return None


def _build_user_message(ticker: str, company_name: str, title: str, raw_text: str) -> str:
    return f"""종목코드: {ticker}
회사명: {company_name}
공시제목: {title}

공시 원문:
{raw_text[:3500]}
"""


def _provider_name() -> str:
    return "Groq" if settings.groq_api_key else "Cerebras"


async def analyze_disclosure(
    ticker: str,
    company_name: str,
    title: str,
    raw_text: str,
    brief: bool = False,
) -> CerebrasAnalysisOutput:
    client = _pick_llm_client()
    if client is None:
        logger.warning("No LLM API key configured (neither GROQ_API_KEY nor CEREBRAS_API_KEY)")
        return _safe_analysis_fallback("No LLM API key configured")

    model = settings.groq_model
    provider = "Groq"

    try:
        system_prompt = BRIEF_ANALYSIS_PROMPT if brief else ANALYSIS_SYSTEM_PROMPT
        max_tokens = 150 if brief else 1200

        async with _llm_semaphore:
            response = await client.chat.completions.create(
                model=model,
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
            return _safe_analysis_fallback(f"Empty {provider} response")

        parsed = json.loads(content)
        return CerebrasAnalysisOutput(
            llm_summary=parsed.get("llm_summary", ""),
            key_metrics=[KeyMetricItem(**m) for m in parsed.get("key_metrics", [])],
        )

    except json.JSONDecodeError as e:
        return _safe_analysis_fallback(f"JSON parse error: {e}")
    except ImportError:
        logger.warning("openai package not installed")
        return _safe_analysis_fallback("openai package not installed")
    except Exception as e:
        logger.error(f"{provider} analysis call failed: {e}", exc_info=True)
        return _safe_analysis_fallback(f"{provider} API error: {e}")


async def analyze_ambiguity(
    ticker: str,
    company_name: str,
    title: str,
    raw_text: str,
) -> CerebrasAmbiguityOutput:
    client = _pick_llm_client()
    if client is None:
        logger.warning("No LLM API key configured (neither GROQ_API_KEY nor CEREBRAS_API_KEY)")
        return _safe_ambiguity_fallback("No LLM API key configured")

    model = settings.groq_ambiguity_model
    provider = "Groq"

    try:
        async with _llm_semaphore:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": AMBIGUITY_SYSTEM_PROMPT},
                    {"role": "user", "content": _build_user_message(ticker, company_name, title, raw_text)},
                ],
                temperature=0.1,
                max_tokens=400,
                response_format={"type": "json_object"},
            )

        content = response.choices[0].message.content
        if not content:
            return _safe_ambiguity_fallback(f"Empty {provider} response")

        parsed = json.loads(content)
        return CerebrasAmbiguityOutput(
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
        logger.error(f"{provider} ambiguity call failed: {e}", exc_info=True)
        return _safe_ambiguity_fallback(f"{provider} API error: {e}")
