"""
Groq LLM service for DART0s.

Calls Groq API with the B-2 system prompt, parses structured JSON output.
LLM does NOT compute scores — only classifies category + extracts flags.
"""

import json
import logging
from typing import Optional, List, Any
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# B-2 System Prompt (verbatim from spec)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """당신은 30년 경력의 대한민국 주식시장 트레이더이며, DART 공시 원문을 즉시 해석하는 역할을 맡고 있습니다.

당신의 임무는 딱 두 가지입니다:
1. 이 공시를 아래 6개 대분류 중 하나로 분류하고, 세부 판별에 필요한 정성적 사실관계(flag)를 원문에서 추출한다.
2. 이 공시가 투자자를 속이려는 트랩(예: 배정대상 실체 불분명, 비정상적으로 긴 납입일정, 계약상대방 비공개 등)인지, 아니면 진짜 모멘텀인지 트레이더 관점에서 근거를 들어 서술한다.

절대로 점수(dvi_score)를 직접 계산하지 마십시오. 점수는 별도 시스템이 계산합니다. 당신은 category, sub_rule_id, 그리고 필요한 flag 값만 정확히 추출하면 됩니다.

대분류:
- CAPITAL_RAISING (자금조달: 유증/CB/BW)
- BIOTECH (바이오/제약: 임상/허가/기술이전)
- BUSINESS_CONTRACT (영업계약: 공급계약/무상증자)
- EARNINGS (실적/재무: 흑자전환/어닝서프라이즈/적자)
- SHAREHOLDER_RETURN (주주환원/지배구조: 자사주/최대주주변경)
- DELISTING_RISK (상장유지 리스크: 감사의견/횡령배임/감자 - 해당 시 반드시 표시)

STRICT OUTPUT: 아래 JSON 스키마로만 응답하십시오. 마크다운, 설명 텍스트 절대 금지.

{
  "ticker": "String (6자리 종목코드)",
  "company_name": "String",
  "title": "String (공시 제목)",
  "category": "String (위 6개 대분류 중 하나)",
  "sub_rule_flags": {
    "third_party_target": "CONGLOMERATE | AFFILIATE | SHELL_OR_PE | null",
    "payment_delay_days": "Number | null",
    "cb_purpose": "FACILITY_OR_ACQUISITION | OPERATING_OR_DEBT | null",
    "deal_amount_disclosed": "Boolean | null",
    "counterparty_disclosed": "Boolean | null",
    "revenue_ratio_estimate": "Number (percent) | null",
    "major_holder_acquirer_type": "MAJOR_OR_FUND | NEW_ENTITY | null",
    "delisting_hard_fail_detected": "Boolean"
  },
  "deceptive_pattern_detected": "Boolean",
  "momentum_authenticity": "String ('HIGH' | 'MEDIUM' | 'LOW')",
  "llm_summary": "String (2-3문장, 직설적인 트레이더 톤, 군더더기 없이)",
  "key_metrics": [
    {
      "label": "String (예: '배정 대상', '납입 일정', '승인 기관')",
      "value": "String",
      "status": "String ('POSITIVE' | 'NEUTRAL' | 'NEGATIVE')"
    }
  ]
}

주의사항:
- 원문에 명시되지 않은 정보는 절대 추측하지 말고 null로 표기하십시오.
- delisting_hard_fail_detected가 true인 경우 다른 필드는 최소한으로 채우고 이 필드를 최우선으로 정확히 표시하십시오.
- key_metrics는 최대 3개까지만 추출하십시오."""


# ---------------------------------------------------------------------------
# Output model
# ---------------------------------------------------------------------------

class KeyMetricItem(BaseModel):
    label: str
    value: str
    status: str  # POSITIVE | NEUTRAL | NEGATIVE


class SubRuleFlags(BaseModel):
    third_party_target: Optional[str] = None
    payment_delay_days: Optional[float] = None
    cb_purpose: Optional[str] = None
    deal_amount_disclosed: Optional[bool] = None
    counterparty_disclosed: Optional[bool] = None
    revenue_ratio_estimate: Optional[float] = None
    major_holder_acquirer_type: Optional[str] = None
    delisting_hard_fail_detected: bool = False


class GroqOutput(BaseModel):
    ticker: str
    company_name: str
    title: str
    category: str
    sub_rule_flags: SubRuleFlags
    deceptive_pattern_detected: bool = False
    momentum_authenticity: str = "MEDIUM"  # HIGH | MEDIUM | LOW
    llm_summary: str = ""
    key_metrics: List[KeyMetricItem] = []


# ---------------------------------------------------------------------------
# Safe fallback
# ---------------------------------------------------------------------------

def _safe_fallback(error_msg: str) -> GroqOutput:
    """Return a minimal safe response when LLM call or parsing fails."""
    logger.warning(f"Groq LLM fallback triggered: {error_msg}")
    return GroqOutput(
        ticker="",
        company_name="",
        title="",
        category="",
        deceptive_pattern_detected=False,
        momentum_authenticity="MEDIUM",
        llm_summary="LLM 분석 실패",
        key_metrics=[],
    )


# ---------------------------------------------------------------------------
# Main API
# ---------------------------------------------------------------------------

async def analyze_disclosure(
    ticker: str,
    company_name: str,
    title: str,
    raw_text: str,
) -> GroqOutput:
    """
    Call Groq API to analyze a disclosure.

    Returns parsed GroqOutput. On any failure, returns safe fallback.
    """
    if not settings.groq_api_key:
        logger.warning("GROQ_API_KEY not set — skipping LLM analysis")
        return _safe_fallback("GROQ_API_KEY not configured")

    try:
        from groq import AsyncGroq

        client = AsyncGroq(api_key=settings.groq_api_key)

        user_message = f"""종목코드: {ticker}
회사명: {company_name}
공시제목: {title}

공시 원문:
{raw_text[:8000]}  # Truncate to avoid token limits
"""

        response = await client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.1,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            return _safe_fallback("Empty LLM response")

        # Parse JSON
        data = json.loads(content)

        # Validate with pydantic
        result = GroqOutput(**data)

        # Override ticker/company/title from known data
        result.ticker = ticker
        result.company_name = company_name
        result.title = title

        return result

    except json.JSONDecodeError as e:
        return _safe_fallback(f"JSON parse error: {e}")
    except ImportError:
        logger.warning("groq package not installed — skipping LLM")
        return _safe_fallback("groq package not installed")
    except Exception as e:
        logger.error(f"Groq LLM call failed: {e}", exc_info=True)
        return _safe_fallback(f"Groq API error: {e}")
