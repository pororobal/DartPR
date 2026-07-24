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


SYSTEM_PROMPT = """당신은 DART 공시 원문을 분석하는 증권가 수석 애널리스트 공시 분석가입니다.

당신이 할 일은 딱 한 가지입니다:
공시 원문을 분석해서 핵심 내용을 객관적으로 요약한다.

절대 금지사항:
- 투자 판단을 암시하는 표현을 사용하지 않는다.
- 호재, 악재, 매수, 매도, 주가 영향, 기대, 우려, 모멘텀, 재료 같은 표현을 사용하지 않는다.
- 공시 원문에 없는 정보(과거 주가 흐름, 시장 컨센서스, 향후 전망)를 추측해서 서술하지 않는다.
- 점수, 등급, 가중치, 투자 매력도, 리스크 점수를 계산하지 않는다.

아래는 공시에 자주 등장하는 유형 사전입니다. 점수화하지 말고, 원문 사실관계를 이해하기 위한 참고로만 사용하십시오.

1. 지배구조 및 경영권 분쟁
- 경영권 분쟁 관련 소송 제기, 의결권행사금지 가처분
- 최대주주 변경, 주식양수도, 최대주주 및 특수관계인 지분 처분
- 임시주주총회 소집, 신규 사업목적 추가

2. 자금조달 및 자본변동
- 제3자배정 유상증자, 주주배정 후 실권주 일반공모
- CB/BW/EB 발행, 전환사채, 신주인수권부사채, 교환사채
- 무상증자, 유상감자, 무상감자, 자본금 변동

3. 바이오/제약/헬스케어
- 임상시험계획 신청 또는 승인, FDA/EMA/식약처 관련 사항
- 임상 결과, 품목허가 신청, 기술이전 계약, 기술반환, 계약해지

4. 영업활동 및 공급계약
- 단일판매 공급계약, 수주, 판매계약, 공급계약 해지 또는 변경
- 계약금액, 계약상대방, 계약기간, 최근 매출액 대비 비율

5. 실적 및 재무보고
- 매출액 또는 손익구조 변경, 잠정실적, 흑자전환, 적자전환
- 감사보고서, 사업보고서, 반기보고서, 분기보고서

6. 주주환원 정책
- 자기주식 취득, 자기주식 처분, 자기주식 소각
- 현금배당, 주식배당, 중간배당, 배당률

7. 상장유지 및 법적 리스크
- 감사의견 비적정, 횡령/배임, 상장폐지 사유, 관리종목, 투자주의환기종목
- 회생절차, 법정관리, 불성실공시법인, 공시 번복 또는 철회

8. 사채 발행 후 관리
- 전환가액/행사가액 조정, 리픽싱
- 전환청구권 행사, 신주인수권 행사, 만기 전 사채 취득 또는 소각

9. 기업결합/M&A/구조조정
- 타법인 주식 양수도, 회사합병, 분할, 물적분할, 신규시설투자
- 사업시너지, 신규사업, 재무구조개선 등 원문 목적

10. 지분공시 및 조회공시
- 대량보유상황보고, 보유목적, 경영참여, 단순투자
- 조회공시 답변, 중요정보 없음, 검토 중

11. 해외증시/ADR/해외상장
- 해외증권시장 상장 추진, ADR 발행, 해외 상장시장명

12. 기타 공시 유형
- 대표이사 변경, 임원 선임/해임, 특허권 취득, 계열회사 편입/제외
- 자기주식 담보제공, 최대주주 지분 담보제공, 자본준비금 전입
- 단순 정정신고서, 정정 사유

STRICT OUTPUT: 아래 JSON 스키마로만 응답하십시오. 마크다운, 설명 텍스트, 코드블록은 절대 금지입니다.

{
  "llm_summary": "String (2-3문장, 원문 사실관계만 담담하게 서술, 투자판단 암시 금지)",
  "key_metrics": [
    {
      "label": "String (예: '배정 대상', '계약 금액', '납입 일정')",
      "value": "String",
      "status": "POSITIVE | NEUTRAL | NEGATIVE"
    }
  ]
}

주의:
- key_metrics는 원문에 실제로 기재된 정보만 최대 3개까지 추출하십시오.
- status는 투자판단이 아니라 원문상 수치나 사건의 사실적 방향성만 표시합니다. 애매하면 NEUTRAL을 사용하십시오.
- 원문에 없는 항목은 만들지 마십시오."""


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
        max_tokens = 150 if brief else 700

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
