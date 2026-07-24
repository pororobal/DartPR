"""
DART0s Rules Engine — full scoring pipeline.

Pipeline:
  1. check_administrative(title) → ADMINISTRATIVE, score=10, skip LLM
  2. check_hard_fail(raw_text)   → score=0, HIGH_RISK_TRAP, skip LLM
  3. guess_category(title)       → category + sub_rule_flags
  4. compute_score(category, flags, ticker, supabase) → final ScoreResult
  5. LLM only if score >= FEED_VISIBILITY_THRESHOLD
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

HARD_FAIL_KEYWORDS = [
    "감사의견거절",
    "감사의견한정",
    "감사의견부적정",
    "횡령",
    "배임",
    "상장폐지",
    "회생절차",
    "법정관리",
    "무상감자",
    "불성실공시법인",
    "공시번복",
]


@dataclass
class HardFailResult:
    detected: bool
    matched_keyword: Optional[str] = None
    skip_llm: bool = True
    risk_flag: str = ""


@dataclass
class ScoreResult:
    category: str = "OTHER"
    sub_type: str = ""
    sub_rule_id: str = ""
    dvi_score: int = 30
    impact_level: str = "MEDIUM"
    risk_flag: str = ""
    is_feed_visible: bool = False
    skip_llm: bool = False
    deceptive_pattern_detected: Optional[bool] = None
    momentum_authenticity: str = "MEDIUM"


# ---------------------------------------------------------------------------
# Step 1: Administrative disclosure filter (§4)
# ---------------------------------------------------------------------------

# Patterns from the spec — checking title (case-insensitive)
_ADMIN_PATTERNS = [
    "효력발생안내",
    "증권발행실적보고서",
    "동일인등출자계열회사와의상품",
    r"기업설명회",
    r"IR\s*개최",
    "특수관계인과의거래",
    r"주식매수선택권\s*부여",
    "합병등종료보고서",
    "자기주식취득결과보고서",
    "매매거래정지",
    "매매거래정지해제",
    "주주명부폐쇄기간",
    "기준일설정",
    r"정정신고",
    "주요주주특정증권등소유상황보고서",
    r"사외이사의\s*선임",
    r"사외이사의\s*해임",
    r"사외이사의\s*중도퇴임",
    "영업보고서",
]


def check_administrative(title: str) -> bool:
    """Return True if this is an administrative disclosure (skips scoring & LLM)."""
    t = title.replace(" ", "")
    for pattern in _ADMIN_PATTERNS:
        stripped = pattern.replace(r"\s*", "")
        if stripped in t:
            logger.debug(f"Admin pattern matched: {pattern}")
            return True
    return False


# ---------------------------------------------------------------------------
# Step 2: Hard-fail detection (§5-7)
# ---------------------------------------------------------------------------

def check_hard_fail(raw_text: str) -> HardFailResult:
    """Detect FAST-FAIL keywords. These get score=0, risk=HIGH_RISK_TRAP, always visible."""
    for kw in HARD_FAIL_KEYWORDS:
        if kw in raw_text:
            return HardFailResult(
                detected=True,
                matched_keyword=kw,
                risk_flag="HIGH_RISK_TRAP",
            )
    return HardFailResult(detected=False)


# ---------------------------------------------------------------------------
# Keyword extraction helpers
# ---------------------------------------------------------------------------

def _extract_keywords(text: str) -> dict:
    """Extract useful flags from title + raw_text using regex."""
    flags = {}

    # Third-party allotment target
    m = re.search(r"제3자배정.*?(\w+(?:\(주\))?)", text)
    if m:
        flags["third_party_target"] = m.group(1)
    m = re.search(r"3자배정.*?(\w+(?:\(주\))?)", text)
    if m:
        flags["third_party_target"] = m.group(1)

    # CB / BW purpose
    if re.search(r"(전환사채|CB|BW|신주인수권부사채)", text):
        if re.search(r"시설자금", text):
            flags["cb_purpose"] = "시설자금"
        elif re.search(r"타법인증권취득", text):
            flags["cb_purpose"] = "타법인증권취득"
        elif re.search(r"운영자금", text):
            flags["cb_purpose"] = "운영자금"
        elif re.search(r"채무상환", text):
            flags["cb_purpose"] = "채무상환"

    # Capital reduction type
    if re.search(r"무상감자", text):
        flags["capital_reduction_type"] = "무상"
    if re.search(r"유상감자", text):
        flags["capital_reduction_type"] = "유상"

    # Payment delay
    m = re.search(r"납입(\s*)일.*?(\d+)", text)
    if m:
        try:
            flags["payment_delay_days"] = int(m.group(2))
        except ValueError:
            pass

    # BIOTECH
    flags["fda_approval"] = bool(
        re.search(r"(IND|FDA|EMA|식약처).*(승인|신청|허가)", text)
    )
    flags["clinical_hold"] = bool(
        re.search(r"(임상중지|Clinical\s*Hold|보완요구)", text)
    )
    flags["phase3_nda"] = bool(
        re.search(r"(임상3상|NDA|신약허가신청|품목허가)", text)
    )
    flags["tech_transfer"] = bool(re.search(r"기술이전", text))
    flags["tech_return"] = bool(
        re.search(r"(기술반환|라이선스\s*계약\s*해지)", text)
    )
    # Check if tech transfer amount is disclosed (contains 숫자+억/원)
    if flags["tech_transfer"]:
        flags["amount_disclosed"] = bool(
            re.search(r"(\d+[,\d]*)\s*(억|원|달러)", text)
        )
    else:
        flags["amount_disclosed"] = False

    # BUSINESS_CONTRACT
    m = re.search(r"(계약금액|계약\s*금액).*?(\d[\d,]*)\s*(억|원)", text)
    if m:
        try:
            flags["contract_amount"] = int(m.group(2).replace(",", ""))
        except ValueError:
            pass

    m = re.search(r"(최근\s*매출액\s*대비|매출액\s*대비).*?(\d+)\s*%", text)
    if m:
        try:
            flags["revenue_ratio"] = float(m.group(2))
        except ValueError:
            pass

    m = re.search(r"(계약\s*상대방|상대방).*?(\w+(?:\(주\))?)", text)
    if m:
        flags["counterparty_name"] = m.group(2)

    if re.search(r"(계약\s*해지|해지)", text):
        flags["contract_type"] = "해지"
    elif re.search(r"(변경|수정)", text) and re.search(r"감액|(\d+)\s*%", text):
        flags["contract_type"] = "변경"
    elif re.search(r"(신규|체결)", text):
        flags["contract_type"] = "신규"

    # SHAREHOLDER_RETURN
    flags["buyback_and_cancel"] = bool(
        re.search(r"(자사주.*소각|자기주식.*소각)", text)
    )
    flags["buyback_only"] = bool(
        re.search(r"(자사주\s*취득|자기주식\s*취득)", text)
    ) and not flags["buyback_and_cancel"]
    flags["treasury_disposal"] = bool(re.search(r"(자사주\s*처분|자기주식\s*처분)", text))
    flags["stock_option"] = bool(re.search(r"주식매수선택권", text))
    flags["dividend"] = bool(re.search(r"(배당|배당률)", text))
    if flags["dividend"]:
        m = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
        if m:
            try:
                flags["dividend_rate"] = float(m.group(1))
            except ValueError:
                pass

    # EARNINGS
    flags["loss_to_profit"] = bool(re.search(r"흑자전환", text))
    flags["profit_to_loss"] = bool(re.search(r"적자전환", text))
    flags["loss_continued"] = bool(
        re.search(r"(적자지속|영업손실|당기순손실)", text)
    )
    flags["revenue_increase"] = bool(
        re.search(r"(매출.*증가|실적.*개선|영업이익)", text)
    )
    flags["revenue_decrease"] = bool(
        re.search(r"(매출.*감소|실적.*악화)", text)
    )
    m = re.search(r"(매출액|매출).*?(\d[\d,]*)\s*(억|원)", text)
    if m:
        try:
            flags["revenue_amount"] = int(m.group(2).replace(",", ""))
        except ValueError:
            pass

    # M&A / Governance
    flags["management_dispute"] = bool(
        re.search(r"(경영권\s*분쟁|가처분)", text)
    )
    flags["major_holder_change"] = bool(re.search(r"최대주주\s*변경", text))
    m = re.search(r"최대주주\s*변경.*?(\w+(?:\(주\))?)", text)
    if m:
        flags["acquirer_name"] = m.group(1)

    flags["block_trade"] = bool(
        re.search(r"(최대주주.*매도|특수관계인.*매도|장내매도)", text)
    )
    flags["bulk_holding_management"] = bool(
        re.search(r"(대량보유|5%룰).*\s*(경영참여|경영권)", text)
    )
    flags["bulk_holding_investment"] = bool(
        re.search(r"(대량보유|5%룰).*\s*(단순투자)", text)
    )
    flags["equity_acquisition"] = bool(
        re.search(r"(타법인.*양수|지분.*취득)", text)
    )
    flags["split_with_listing"] = bool(
        re.search(r"(물적분할|상장.*언급)", text)
    )
    flags["merger"] = bool(
        re.search(r"(합병|완전자회사\s*흡수)", text)
    )
    flags["overseas_listing"] = bool(
        re.search(r"(해외.*상장|ADR)", text)
    )

    return flags


# ---------------------------------------------------------------------------
# Step 3: Category guesser (keyword-based pre-LLM)
# ---------------------------------------------------------------------------

def guess_category(title: str, raw_text: str, keywords: dict = None) -> tuple[str, dict]:
    if keywords is None:
        keywords = _extract_keywords(f"{title} {raw_text}")
    t = title.upper()

    # Administrative — checked BEFORE this, but guard here too
    if check_administrative(title):
        return ("ADMINISTRATIVE", keywords)

    # DELISTING_RISK / hard fail
    if any(kw in t for kw in [
        "감사의견", "횡령", "배임", "감자", "상장폐지",
        "관리종목", "상장적격성", "회생", "법정관리",
    ]):
        return ("DELISTING_RISK", keywords)

    # SHAREHOLDER_RETURN
    if any(kw in t for kw in ["주식소각", "자기주식소각"]):
        return ("SHAREHOLDER_RETURN", keywords)
    if any(kw in t for kw in ["자사주취득", "자기주식취득"]):
        return ("SHAREHOLDER_RETURN", keywords)
    if any(kw in t for kw in ["자기주식처분"]):
        return ("SHAREHOLDER_RETURN", keywords)
    if any(kw in t for kw in ["배당", "주주환원"]):
        return ("SHAREHOLDER_RETURN", keywords)

    # CAPITAL_RAISING
    if any(kw in t for kw in [
        "유상증자", "주주배정", "제3자배정", "3자배정",
    ]):
        return ("CAPITAL_RAISING", keywords)
    if any(kw in t for kw in [
        "CB 발행", "BW 발행", "전환사채", "전환청구권",
        "신주인수권", "사채발행",
    ]):
        return ("CAPITAL_RAISING", keywords)
    if any(kw in t for kw in ["무상증자", "유상증자"]):
        return ("CAPITAL_RAISING", keywords)

    # BUSINESS_CONTRACT
    if any(kw in t for kw in ["단일판매", "공급계약", "판매계약", "수주"]):
        return ("BUSINESS_CONTRACT", keywords)
    if any(kw in t for kw in ["계약", "공급"]):
        return ("BUSINESS_CONTRACT", keywords)

    # EARNINGS
    if any(kw in t for kw in ["적자전환", "적자지속", "영업손실", "당기순손실"]):
        return ("EARNINGS", keywords)
    if any(kw in t for kw in ["흑자전환", "영업이익", "매출액증가", "실적개선"]):
        return ("EARNINGS", keywords)
    if any(kw in t for kw in ["감사보고서", "사업보고서", "반기보고서", "분기보고서"]):
        return ("EARNINGS", keywords)
    if any(kw in t for kw in ["실적", "매출액"]):
        return ("EARNINGS", keywords)

    # BIOTECH
    if any(kw in t for kw in ["임상", "FDA", "식약처", "품목허가", "신약", "기술이전", "IND"]):
        return ("BIOTECH", keywords)

    # M&A / governance (SHAREHOLDER_RETURN used for these too)
    if any(kw in t for kw in ["합병", "분할", "최대주주변경"]):
        return ("SHAREHOLDER_RETURN", keywords)
    if any(kw in t for kw in ["소송", "가처분"]):
        return ("SHAREHOLDER_RETURN", keywords)
    if any(kw in t for kw in ["대량보유", "주식등의대량보유", "지분"]):
        return ("SHAREHOLDER_RETURN", keywords)

    return ("OTHER", keywords)


# ---------------------------------------------------------------------------
# Step 4: Scoring per category (§5)
# ---------------------------------------------------------------------------

def _is_conglomerate(name: str, supabase=None) -> bool:
    """Check if a company name matches a known conglomerate affiliate."""
    if not name or not supabase:
        return False
    try:
        result = (
            supabase.table("conglomerate_groups")
            .select("id")
            .ilike("affiliate_name", name.replace("(주)", "").strip())
            .limit(1)
            .execute()
        )
        return bool(result.data)
    except Exception:
        return False


def _count_disclosures_by_ticker(
    supabase, ticker: str, category: str = None, sub_type: str = None,
    since_days: int = 730
) -> int:
    """Count past disclosures for a ticker (default: 2 years)."""
    try:
        since = (datetime.now(timezone.utc) - timedelta(days=since_days)).isoformat()
        query = (
            supabase.table("disclosures")
            .select("id", count="exact")
            .eq("ticker", ticker)
            .gte("published_at", since)
        )
        if category:
            query = query.eq("category", category)
        if sub_type:
            query = query.eq("sub_type", sub_type)
        result = query.execute()
        return result.count if hasattr(result, "count") else len(result.data or [])
    except Exception as e:
        logger.warning(f"DB count failed for {ticker}: {e}")
        return 0


def _get_earnings_history(supabase, ticker: str) -> list[dict]:
    """
    Fetch past EARNINGS disclosures for a ticker to determine earnings trend.
    Returns list of records with sub_type info.
    """
    try:
        result = (
            supabase.table("disclosures")
            .select("sub_type, published_at")
            .eq("ticker", ticker)
            .eq("category", "EARNINGS")
            .order("published_at", desc=True)
            .limit(10)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.warning(f"Earnings history lookup failed for {ticker}: {e}")
        return []


def _get_shareholder_history(supabase, ticker: str) -> list[dict]:
    """Fetch past SHAREHOLDER_RETURN disclosures for a ticker."""
    try:
        result = (
            supabase.table("disclosures")
            .select("sub_type, published_at")
            .eq("ticker", ticker)
            .eq("category", "SHAREHOLDER_RETURN")
            .order("published_at", desc=True)
            .limit(10)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.warning(f"Shareholder history lookup failed for {ticker}: {e}")
        return []


def _get_major_holder_change_count(supabase, ticker: str) -> int:
    """Count how many times the max shareholder has changed in the past 2 years."""
    return _count_disclosures_by_ticker(
        supabase, ticker, sub_type="최대주주변경", since_days=730
    )


# ---------------------------------------------------------------------------
# Per-category scoring functions
# ---------------------------------------------------------------------------

def _score_capital_raising(keywords: dict, ticker: str = None, supabase=None) -> tuple:
    """§5-1 자금조달 scoring."""
    target = keywords.get("third_party_target", "")

    # 제3자배정
    if target or keywords.get("third_party_target"):
        # Check if target is a conglomerate
        if supabase and _is_conglomerate(target, supabase):
            return (95, "CAPITAL_RAISING_THIRD_PARTY_CONGLO", "", "")
        # Check if target is a fund/private equity
        if any(k in target for k in ["조합", "투자조합", "사모"]):
            return (20, "CAPITAL_RAISING_THIRD_PARTY_PE", "", "")

        # Check if target is major shareholder/executive
        if any(k in target for k in ["최대주주", "대표이사", "임원"]):
            return (55, "CAPITAL_RAISING_THIRD_PARTY_INSIDER", "", "")

        # General third-party
        return (55, "CAPITAL_RAISING_THIRD_PARTY_GENERAL", "", "")

    # 주주배정 + 일반공모
    if any(k in title_keywords(keywords, ["주주배정", "일반공모"])):
        return (10, "CAPITAL_RAISING_RIGHTS_OFFERING", "", "")

    # 무상증자
    if title_keywords(keywords, ["무상증자"]):
        return (68, "CAPITAL_RAISING_FREE_INCREASE", "", "")

    # CB / BW
    cb_purpose = keywords.get("cb_purpose", "")
    if cb_purpose:
        if cb_purpose in ("시설자금", "타법인증권취득"):
            return (50, "CAPITAL_RAISING_CB_FACILITY", "", "")
        else:
            return (15, "CAPITAL_RAISING_CB_WORKING", "", "")

    # 감자
    reduction_type = keywords.get("capital_reduction_type", "")
    if reduction_type == "무상":
        return (0, "CAPITAL_RAISING_FREE_REDUCTION", "HIGH_RISK_TRAP", "")
    if reduction_type == "유상":
        return (60, "CAPITAL_RAISING_PAID_REDUCTION", "", "")

    # Payment delay penalty
    delay = keywords.get("payment_delay_days", 0)
    base_score = 30
    if delay >= 91:
        base_score = max(0, base_score - 20)
        return (base_score, "CAPITAL_RAISING_DELAYED_PAYMENT", "", "")

    return (30, "CAPITAL_RAISING_GENERAL", "", "")


def _score_biotech(keywords: dict) -> tuple:
    """§5-2 바이오/제약 scoring."""
    # IND + FDA/EMA approval → 95
    if keywords.get("fda_approval"):
        return (95, "BIOTECH_FDA_APPROVAL", "", "")

    # 임상중지/Clinical Hold → FAST-FAIL
    if keywords.get("clinical_hold"):
        return (0, "BIOTECH_CLINICAL_HOLD", "HIGH_RISK_TRAP", "")

    # 임상3상 + 품목허가/NDA → 77
    if keywords.get("phase3_nda"):
        return (77, "BIOTECH_PHASE3_NDA", "", "")

    # 기술이전
    if keywords.get("tech_transfer"):
        if keywords.get("amount_disclosed"):
            return (98, "BIOTECH_TECH_TRANSFER_AMOUNT", "", "")
        else:
            return (55, "BIOTECH_TECH_TRANSFER_NO_AMOUNT", "", "")

    # 기술반환/라이선스 계약해지
    if keywords.get("tech_return"):
        return (1, "BIOTECH_TECH_RETURN", "", "")

    return (30, "BIOTECH_GENERAL", "", "")


def _score_business_contract(keywords: dict, ticker: str = None, supabase=None) -> tuple:
    """§5-3 영업계약 scoring with revenue ratio."""
    ratio = keywords.get("revenue_ratio")
    counterparty = keywords.get("counterparty_name", "")
    contract_type = keywords.get("contract_type", "신규")

    # 해지/변경(20%↑ 감액)
    if contract_type == "해지":
        return (5, "BUSINESS_CONTRACT_TERMINATED", "", "")
    if contract_type == "변경":
        return (5, "BUSINESS_CONTRACT_MODIFIED", "", "")

    counterparty_disclosed = bool(counterparty)
    base_score = 15  # 비공개 default

    if counterparty_disclosed and ratio is not None:
        if ratio >= 100:
            base_score = 100
        elif ratio >= 50:
            base_score = 90
        elif ratio >= 30:
            base_score = 75
        elif ratio >= 10:
            base_score = 50
        else:
            base_score = 20
    elif counterparty_disclosed:
        base_score = 20
    else:
        base_score = 15

    # 가중치: 신규 거래처 × 1.1, 기존 × 0.85
    if supabase and ticker and counterparty:
        past = _count_disclosures_by_ticker(supabase, ticker)
        if past > 0:
            # Check if this counterparty appeared before (rough: search in raw_text matches)
            is_new = True  # optimistic default — we can refine later
            base_score = int(base_score * (1.1 if is_new else 0.85))

    sub_id = f"BUSINESS_CONTRACT_{int(ratio) if ratio else 'NA'}_PCT"
    return (min(base_score, 100), sub_id, "", "")


def _score_earnings(keywords: dict, ticker: str = None, supabase=None) -> tuple:
    """§5-4 실적/재무 scoring with DB history lookup."""
    loss_to_profit = keywords.get("loss_to_profit", False)
    profit_to_loss = keywords.get("profit_to_loss", False)
    loss_continued = keywords.get("loss_continued", False)
    revenue_increase = keywords.get("revenue_increase", False)
    revenue_decrease = keywords.get("revenue_decrease", False)

    # Try DB history lookup
    if supabase and ticker:
        history = _get_earnings_history(supabase, ticker)
        loss_count = sum(
            1 for h in history if h.get("sub_type", "") in
            ("적자전환", "적자지속", "영업손실")
        )
        profit_count = sum(
            1 for h in history if h.get("sub_type", "") in
            ("흑자전환", "영업이익", "매출증가")
        )

        # 흑자전환 — check past
        if loss_to_profit:
            if loss_count >= 3:
                return (90, "EARNINGS_LOSS_TO_PROFIT_3Q", "", "흑자전환")
            elif loss_count >= 1:
                return (71, "EARNINGS_LOSS_TO_PROFIT_1Q", "", "흑자전환")
            # fallback to no-history rule

        # 적자전환
        if profit_to_loss:
            if profit_count >= 3:
                return (6, "EARNINGS_PROFIT_TO_LOSS_3Q", "", "적자전환")
            elif profit_count >= 1:
                return (10, "EARNINGS_PROFIT_TO_LOSS_1Q", "", "적자전환")

        # 적자지속
        if loss_continued:
            if loss_count >= 4:
                return (3, "EARNINGS_LOSS_CONTINUED_4Q", "", "적자지속")
            else:
                return (8, "EARNINGS_LOSS_CONTINUED", "", "적자지속")

    # Fallback (no history or no DB)
    if loss_to_profit:
        return (65, "EARNINGS_LOSS_TO_PROFIT_NO_HISTORY", "", "흑자전환")
    if profit_to_loss:
        return (10, "EARNINGS_PROFIT_TO_LOSS_NO_HISTORY", "", "적자전환")
    if loss_continued:
        return (8, "EARNINGS_LOSS_CONTINUED", "", "적자지속")

    # 매출 변동
    if revenue_increase and not revenue_decrease:
        return (60, "EARNINGS_REVENUE_INCREASE", "", "매출증가")
    if revenue_decrease and not revenue_increase:
        return (10, "EARNINGS_REVENUE_DECREASE", "", "매출감소")

    return (30, "EARNINGS_GENERAL", "", "일반실적")


def _score_shareholder_return(keywords: dict, ticker: str = None, supabase=None) -> tuple:
    """§5-5 주주환원 scoring with repetition check."""
    buyback_cancel = keywords.get("buyback_and_cancel", False)
    buyback_only = keywords.get("buyback_only", False)
    treasury_disposal = keywords.get("treasury_disposal", False)
    stock_option = keywords.get("stock_option", False)
    dividend = keywords.get("dividend", False)
    dividend_rate = keywords.get("dividend_rate", 0)

    # Check history
    is_first_buyback = True
    is_first_dividend = True
    past_cancels = 0
    past_dividends = 0

    if supabase and ticker:
        history = _get_shareholder_history(supabase, ticker)
        past_cancels = sum(
            1 for h in history
            if (h.get("sub_type") or "") in ("자사주소각", "취득+소각")
        )
        past_dividends = sum(
            1 for h in history
            if (h.get("sub_type") or "").startswith("배당")
        )

        is_first_buyback = past_cancels < 2
        is_first_dividend = past_dividends == 0

    # 자사주 취득+소각
    if buyback_cancel:
        if is_first_buyback:
            return (96, "SHAREHOLDER_FIRST_BUYBACK_CANCEL", "", "취득+소각")
        else:
            return (85, "SHAREHOLDER_REPEAT_BUYBACK_CANCEL", "", "취득+소각")

    # 자사주 취득(소각 미언급)
    if buyback_only:
        return (54, "SHAREHOLDER_BUYBACK_ONLY", "", "자사주취득")

    # 자사주 처분
    if treasury_disposal:
        if stock_option:
            return (45, "SHAREHOLDER_DISPOSAL_STOCK_OPTION", "", "자사주처분")
        return (10, "SHAREHOLDER_DISPOSAL_OPERATING", "", "자사주처분")

    # 배당
    if dividend:
        if is_first_dividend:
            return (90, "SHAREHOLDER_FIRST_DIVIDEND", "", "최초배당")
        if dividend_rate >= 5:
            return (72, "SHAREHOLDER_DIVIDEND_HIGH", "", "배당")
        return (55, "SHAREHOLDER_DIVIDEND_LOW", "", "배당")

    return (30, "SHAREHOLDER_GENERAL", "", "")


def _score_shareholder_ma(keywords: dict, ticker: str = None, supabase=None) -> tuple:
    """§5-6 지배구조/M&A/지분공시 scoring."""
    # 경영권분쟁/가처분
    if keywords.get("management_dispute", False):
        return (100, "MA_MANAGEMENT_DISPUTE", "", "경영권분쟁")

    # 최대주주변경
    if keywords.get("major_holder_change", False):
        acquirer = keywords.get("acquirer_name", "")
        change_count = 0
        if supabase and ticker:
            change_count = _get_major_holder_change_count(supabase, ticker)

        # 양수인 대기업집단
        if supabase and acquirer and _is_conglomerate(acquirer, supabase):
            if change_count <= 1:
                return (84, "MA_MAJOR_CHANGE_CONGLO_FIRST", "", "최대주주변경")
            else:
                return (50, "MA_MAJOR_CHANGE_CONGLO_REPEAT", "", "최대주주변경")

        # 양수인 설립 1년 미만 (rough check: name contains "신설" or "설립")
        if acquirer and any(k in acquirer for k in ["신설", "설립"]):
            return (12, "MA_MAJOR_CHANGE_NEWLY_FORMED", "", "최대주주변경")

        return (84, "MA_MAJOR_CHANGE_GENERAL", "", "최대주주변경")

    # 최대주주/특수관계인 장내매도
    if keywords.get("block_trade", False):
        return (6, "MA_BLOCK_TRADE", "", "장내매도")

    # 대량보유(5%룰) + 경영참여
    if keywords.get("bulk_holding_management", False):
        return (90, "MA_BULK_HOLDING_MANAGEMENT", "", "대량보유")

    # 대량보유 + 단순투자
    if keywords.get("bulk_holding_investment", False):
        return (50, "MA_BULK_HOLDING_INVESTMENT", "", "대량보유")

    # 타법인지분양수 + 시너지/신규사업
    if keywords.get("equity_acquisition", False):
        return (72, "MA_EQUITY_ACQUISITION", "", "지분양수")

    # 물적분할 + 상장언급
    if keywords.get("split_with_listing", False):
        return (3, "MA_SPLIT_WITH_LISTING", "", "물적분할")

    # 회사합병
    if keywords.get("merger", False):
        return (77, "MA_MERGER", "", "합병")

    # 해외증시/ADR 상장
    if keywords.get("overseas_listing", False):
        return (96, "MA_OVERSEAS_LISTING", "", "해외상장")

    return (30, "MA_GENERAL", "", "")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def title_keywords(keywords: dict, search_terms: list[str]) -> bool:
    """Check if any of the search terms appear in keywords context."""
    return any(kw in str(keywords.get(key, "")) for key in keywords for kw in search_terms)


def _impact_level_from_score(score: int) -> str:
    """Map DVI score to impact_level values matching DB constraint (HIGH_IMPACT, NORMAL, LOW_IMPACT)."""
    if score >= 90:
        return "HIGH_IMPACT"
    elif score >= 40:
        return "NORMAL"
    else:
        return "LOW_IMPACT"


# ---------------------------------------------------------------------------
# Main evaluation pipeline
# ---------------------------------------------------------------------------

def evaluate_disclosure(
    title: str,
    raw_text: str,
    ticker: str = "",
    supabase=None,
) -> ScoreResult:
    """
    Full scoring pipeline.

    Returns ScoreResult with category, score, risk_flag, etc.
    """
    # Step 1: Administrative check
    if check_administrative(title):
        return ScoreResult(
            category="ADMINISTRATIVE",
            sub_rule_id="ADMIN_DISCLOSURE",
            dvi_score=10,
            impact_level="LOW_IMPACT",
            is_feed_visible=False,
            skip_llm=True,
        )

    # Step 2: Hard-fail check
    hard_fail = check_hard_fail(raw_text)
    if hard_fail.detected:
        return ScoreResult(
            category="DELISTING_RISK",
            sub_rule_id=f"HARD_FAIL_{hard_fail.matched_keyword}",
            dvi_score=0,
            impact_level="HIGH_IMPACT",
            risk_flag="HIGH_RISK_TRAP",
            is_feed_visible=True,
            skip_llm=True,
            deceptive_pattern_detected=True,
            momentum_authenticity="LOW",
        )

    # Step 3: Category guess + keyword extraction
    combined = f"{title} {raw_text[:3000]}"
    keywords = _extract_keywords(combined)
    category, _ = guess_category(title, raw_text, keywords)

    # Step 4: Compute score
    score_result = _route_category_scoring(category, keywords, ticker, supabase)
    score = score_result["score"]
    sub_id = score_result["sub_id"]
    risk_flag = score_result.get("risk_flag", "")
    sub_type = score_result.get("sub_type", "")

    # If a rule flagged HIGH_RISK_TRAP, override
    if risk_flag == "HIGH_RISK_TRAP":
        return ScoreResult(
            category=category,
            sub_type=sub_type,
            sub_rule_id=sub_id,
            dvi_score=0,
            impact_level="HIGH_IMPACT",
            risk_flag="HIGH_RISK_TRAP",
            is_feed_visible=True,
            skip_llm=True,
            deceptive_pattern_detected=True,
            momentum_authenticity="LOW",
        )

    # Step 5: Determine visibility + LLM
    is_feed_visible = score >= 80
    skip_llm = score < 80  # Only run LLM for 80+

    return ScoreResult(
        category=category,
        sub_type=sub_type,
        sub_rule_id=sub_id,
        dvi_score=score,
        impact_level=_impact_level_from_score(score),
        risk_flag=risk_flag,
        is_feed_visible=is_feed_visible,
        skip_llm=skip_llm,
    )


def _route_category_scoring(
    category: str,
    keywords: dict,
    ticker: str = None,
    supabase=None,
) -> dict:
    """Route to category-specific scoring function."""
    if category == "ADMINISTRATIVE":
        return {"score": 10, "sub_id": "ADMIN_DISCLOSURE"}

    if category == "CAPITAL_RAISING":
        s, sid, risk, st = _score_capital_raising(keywords, ticker, supabase)
        return {"score": s, "sub_id": sid, "risk_flag": risk, "sub_type": st}

    if category == "BIOTECH":
        s, sid, risk, st = _score_biotech(keywords)
        return {"score": s, "sub_id": sid, "risk_flag": risk, "sub_type": st}

    if category == "BUSINESS_CONTRACT":
        s, sid, risk, st = _score_business_contract(keywords, ticker, supabase)
        return {"score": s, "sub_id": sid, "sub_type": st}

    if category == "EARNINGS":
        s, sid, risk, st = _score_earnings(keywords, ticker, supabase)
        return {"score": s, "sub_id": sid, "sub_type": st}

    if category == "SHAREHOLDER_RETURN":
        # Try M&A scoring first, then shareholder return
        ma_s, ma_sid, risk, st = _score_shareholder_ma(keywords, ticker, supabase)
        # If no M&A-specific match (score=30 generic), try SH scoring
        if ma_sid == "MA_GENERAL":
            s, sid, risk, st = _score_shareholder_return(keywords, ticker, supabase)
            return {"score": s, "sub_id": sid, "risk_flag": risk, "sub_type": st}
        return {"score": ma_s, "sub_id": ma_sid, "risk_flag": risk, "sub_type": st}

    if category == "DELISTING_RISK":
        return {"score": 0, "sub_id": "DELISTING_RISK", "risk_flag": "HIGH_RISK_TRAP"}

    # OTHER / fallback
    return {"score": 30, "sub_id": "OTHER_DEFAULT"}
