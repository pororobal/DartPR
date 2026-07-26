"""
Groq LLM service for DartPR.

The LLM only summarizes DART disclosure facts and extracts metrics. It does
not compute scores or imply investment judgment.
"""

import asyncio
import json
import logging
from typing import List, Optional

from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)
_groq_semaphore = asyncio.Semaphore(1)


SYSTEM_PROMPT = """당신은 DART 공시 원문을 분석하는 증권사 애널리스트입니다.
투자자에게 진짜 유용한 인사이트를 제공하는 것이 목표입니다.

원칙:
1. 공시 원문에 있는 사실만으로 분석하십시오. 원문에 없는 정보는 절대 추가하지 마십시오.
2. 핵심 내용을 요약할 때 단순한 사실 나열이 아니라, **그 사실이 투자자에게 어떤 의미인지**를 1-2문장으로 설명하십시오.
3. "~을 의미", "~의 신호", "~에 해당", "~가 예상됨" 같은 맥락 설명은 허용됩니다.
4. 수치가 있다면 반드시 언급하고, 전년 대비 또는 이전 공시 대비 증감도 포함하십시오.
5. key_metrics는 원문에 실제 기재된 핵심 수치만 최대 3개 추출하십시오.

절대 금지:
- ❌ "매수/매도/투자 추천", "주가 상승/하락 예상" → 투자 판단 금지
- ❌ 원문에 없는 정보, 시장 루머, 과거 주가 패턴 추측
- ❌ "호재/악재/재료/모멘텀" 같은 용어 사용 (원문 분석으로 의미는 전달하되 레이블링 금지)

좋은 예 (허용):
- "자사주를 취득해 소각하는 것은 발행주식 총수를 줄여 주당 가치를 높이는 효과"
- "운영자금 목적의 CB 발행은 이자 부담 없이 자금을 조달하나, 향후 전환 시 희석 우려"
- "영업외손익에 의한 흑자전환은 일회성 요인이므로 실질적 수익성 개선으로 보기 어려움"
- "계약 규모가 최근 매출액 대비 85%로, 실적에 미치는 영향이 큰 대규모 계약"
- "최대주주가 대기업 계열사로 변경되어 재무적 안정성 및 사업 시너지 기대"
- "CB 전환가액이 현 주가 대비 20% 낮게 설정되어 조기 전환 리스크 존재"

나쁜 예 (금지):
- "동사는 CB를 발행했다" (의미 없음. 왜 발행했는지, 어떤 영향인지 서술해야 함)
- "투자자들은 긍정적으로 봐야 한다" (투자 판단 금지)
- "주가가 상승할 것으로 예상된다" (주가 예측 금지)
- "이는 호재다" (레이블링 금지)

아래는 공시 유형별 분석 시 참고할 맥락입니다.
단순히 분류용이며, 이걸 그대로 복사하지 말고 원문에 맞게 서술하십시오.

1. 지배구조 및 경영권 분쟁
- 경영권 분쟁 관련 소송 제기, 의결권행사금지 가처분 → 분쟁 장기화 시 의사결정 지연 및 주주가치 훼손 가능성
- 최대주주 변경 → 누가 인수하는지가 핵심 (대기업 계열사인지, 재무적 투자자인지)

2. 자금조달 및 자본변동
- 제3자배정 유상증자 → 대상자가 누구인지가 가장 중요 (대기업 계열사 = 긍정, PE조합 = 중립, 불특정 = 부정)
- CB 발행 → 자금 사용 목적(시설/운영/채무상환)과 전환가액 수준이 핵심
- CB 리픽싱(전환가액 하향) → 기존 주주 희석 우려 가중

3. 바이오/제약
- FDA/식약처 승인 → 기술력 입증 및 상업화 첫걸음
- 임상 중지 → 기대가치 급락, 사실상 자산가치 훼손
- 기술이전 계약 → 규모 공개 여부가 중요 (미공개시 불확실성)

4. 영업계약
- 계약 규모(금액)와 상대방이 핵심 정보
- 계약 규모가 최근 매출액 대비 몇 %인지가 중요도 판단 기준
- 해지/변경 → 기존 매출에 차질 발생 여부 확인

5. 실적
- 흑자전환 → 영업이익 기준인지, 영업외손익 포함인지 구분 필수
- 적자전환 → 일회성 요인인지 구조적 요인인지 판단
- 감사의견 적정 → 회계 투명성 양호 신호

6. 주주환원
- 자사주 취득+소각 → 발행주식 수 감소 = 주당 가치 증가 효과
- 자사주 처분 → 오버행 부담
- 배당 → 주식배당은 현금 유출 없는 우회 배당으로 실질 가치 낮음
- 자사주 담보 제공 → 유동성 위험 신호

7. 법적 리스크
- 횡령/배임 → 경영진 신뢰도 추락
- 상장폐지/관리종목 → 유통시장 퇴출 위험
- 불성실공시 → 정보 신뢰도 하락

8. 사채 관리
- 전환가액/행사가액 조정 → 방향성이 핵심 (상향=긍정, 하향=부정)
- 전환청구권 행사 → 실제 희석 발생, 주가에 하방 압력

STRICT OUTPUT: 아래 JSON 스키마로만 응답하십시오. 마크다운, 설명 텍스트, 코드블록은 절대 금지입니다.

{
  "llm_summary": "String (2-3문장, 핵심 사실 + 그 사실이 투자자에게 갖는 의미를 간결하게)",
  "key_metrics": [
    {
      "label": "String (예: '배정 대상', '계약 금액', '납입 일정')",
      "value": "String",
      "status": "POSITIVE | NEUTRAL | NEGATIVE"
    }
  ]
}

key_metrics status 기준:
- POSITIVE: 자사주 소각, 최초배당, 영업이익 증가, 기술이전 수취, FDA 승인 등
- NEGATIVE: CB 리픽싱, 적자전환, 자사주 담보, 감사의견 비적정, 횡령 등
- NEUTRAL: 대표이사 변경, 배당(중립), 단순 사채발행 등 애매한 경우"""


class KeyMetricItem(BaseModel):
    label: str
    value: str
    status: str


class GroqOutput(BaseModel):
    ticker: str = ""
    company_name: str = ""
    title: str = ""
    llm_summary: str = ""
    key_metrics: List[KeyMetricItem] = Field(default_factory=list)


def _safe_fallback(error_msg: str) -> GroqOutput:
    """Return a minimal safe response when LLM call or parsing fails."""
    logger.warning(f"Groq LLM fallback triggered: {error_msg}")
    return GroqOutput(
        llm_summary="LLM 분석 실패",
        key_metrics=[],
    )


BRIEF_PROMPT = """당신은 DART 공시 원문을 분석하는 증권사 애널리스트입니다.

공시 원문을 읽고 핵심 사실을 1-2문장으로 간결히 요약하십시오.

투자 판단, 호재/악재 표현, 주가 영향 예측 절대 금지.

STRICT OUTPUT: 아래 JSON 스키마로만 응답하십시오.
{
  "llm_summary": "1-2문장 핵심 요약 (투자판단 금지)",
  "key_metrics": []
}"""


async def analyze_disclosure(
    ticker: str,
    company_name: str,
    title: str,
    raw_text: str,
    brief: bool = False,
) -> GroqOutput:
    """
    Call Groq API to summarize a disclosure.
    When brief=True, returns a 1-2 sentence summary (cheaper, faster).
    When brief=False, returns full analysis with key_metrics.
    """
    if not settings.groq_api_key:
        logger.warning("GROQ_API_KEY not set -- skipping LLM analysis")
        return _safe_fallback("GROQ_API_KEY not configured")

    try:
        from groq import AsyncGroq

        client = AsyncGroq(api_key=settings.groq_api_key)

        user_message = f"""종목코드: {ticker}
회사명: {company_name}
공시제목: {title}

공시 원문:
{raw_text[:3500]}
"""

        system_prompt = BRIEF_PROMPT if brief else SYSTEM_PROMPT
        max_tokens = 150 if brief else 1200

        async with _groq_semaphore:
            response = await client.chat.completions.create(
                model=settings.groq_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.1,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )

        content = response.choices[0].message.content
        if not content:
            return _safe_fallback("Empty LLM response")

        result = GroqOutput(**json.loads(content))
        result.ticker = ticker
        result.company_name = company_name
        result.title = title
        return result

    except json.JSONDecodeError as e:
        return _safe_fallback(f"JSON parse error: {e}")
    except ImportError:
        logger.warning("groq package not installed -- skipping LLM")
        return _safe_fallback("groq package not installed")
    except Exception as e:
        logger.error(f"Groq LLM call failed: {e}", exc_info=True)
        return _safe_fallback(f"Groq API error: {e}")
