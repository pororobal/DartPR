"""
DART0s DVI (Disclosure Value Index) Rules Engine.

Deterministic scoring engine. No LLM, no randomness.
Transcribes A-2 rule table exactly as specified.
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import re


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SubRule:
    id: str
    name: str
    base: float
    multiplier: float
    score_cap: Optional[float] = None
    penalty_condition: Optional[str] = None
    penalty: Optional[float] = None
    penalty_override_score: Optional[float] = None
    llm_flag_required: Optional[str] = None


@dataclass
class CategoryRules:
    category: str
    rules: List[SubRule] = field(default_factory=list)


@dataclass
class HardFailResult:
    detected: bool
    matched_keyword: Optional[str] = None
    score: float = 0.0
    risk_flag: str = "HIGH_RISK_TRAP"
    impact_level: str = "LOW_IMPACT"
    is_feed_visible: bool = True
    skip_llm: bool = True


@dataclass
class ScoreResult:
    dvi_score: float
    sub_rule_id: Optional[str]
    impact_level: str  # HIGH_IMPACT | NORMAL | LOW_IMPACT
    risk_flag: str     # CLEAN | CAUTION | HIGH_RISK_TRAP
    is_feed_visible: bool


# ---------------------------------------------------------------------------
# Hard-fail keywords
# ---------------------------------------------------------------------------

HARD_FAIL_KEYWORDS = [
    "감사의견거절",
    "감사의견한정",
    "감사의견부적정",
    "횡령",
    "배임",
    "감자",
    "상장폐지",
]


def check_hard_fail(raw_text: str) -> HardFailResult:
    """
    Scan raw_text for hard-fail keywords.
    If any found, return score=0 immediately — LLM scoring is skipped.
    """
    for kw in HARD_FAIL_KEYWORDS:
        if kw in raw_text:
            return HardFailResult(
                detected=True,
                matched_keyword=kw,
            )
    return HardFailResult(detected=False)


# ---------------------------------------------------------------------------
# Rule table — verbatim from A-2 spec
# ---------------------------------------------------------------------------

CAPITAL_RAISING = CategoryRules(
    category="CAPITAL_RAISING",
    rules=[
        SubRule(
            id="cr_conglomerate_thirdparty",
            name="대기업/글로벌 빅테크 대상 3자배정 유증",
            base=85, multiplier=1.25, score_cap=100,
            llm_flag_required="third_party_target = CONGLOMERATE",
        ),
        SubRule(
            id="cr_normal_thirdparty",
            name="일반 3자배정 유증 (최대주주/관계사)",
            base=60, multiplier=1.0,
            llm_flag_required="third_party_target = AFFILIATE",
        ),
        SubRule(
            id="cr_shell_company",
            name="사모조합/페이퍼컴퍼니 3자배정 유증",
            base=40, multiplier=0.4,
            penalty_condition="payment_delay_days > 90",
            penalty=20,
            llm_flag_required="third_party_target = SHELL_OR_PE",
        ),
        SubRule(
            id="cr_rights_offering",
            name="주주배정후 실권주 일반공모 유증",
            base=20, multiplier=0.3,
        ),
        SubRule(
            id="cr_cb_bw_facility",
            name="CB/BW 발행 - 시설자금/타법인증권 취득 목적",
            base=55, multiplier=0.9,
            llm_flag_required="cb_purpose = FACILITY_OR_ACQUISITION",
        ),
        SubRule(
            id="cr_cb_bw_operating",
            name="CB/BW 발행 - 운영자금/채무상환 목적",
            base=35, multiplier=0.5,
            llm_flag_required="cb_purpose = OPERATING_OR_DEBT",
        ),
    ],
)

BIOTECH = CategoryRules(
    category="BIOTECH",
    rules=[
        SubRule(
            id="bio_ind_approval",
            name="해외 주요국(FDA/EMA) 임상 1/2상 IND 승인",
            base=70, multiplier=1.35,
        ),
        SubRule(
            id="bio_phase3_nda",
            name="임상 3상 성공 / 품목허가(NDA) 신청",
            base=70, multiplier=1.1,
        ),
        SubRule(
            id="bio_clinical_hold",
            name="임상 중지/보완 요구 (Clinical Hold)",
            base=10, multiplier=0.1,
        ),
        SubRule(
            id="bio_license_out",
            name="기술이전(L/O) 계약",
            base=80, multiplier=1.2,
            penalty_condition="deal_amount_disclosed = false",
            penalty_override_score=60,
            llm_flag_required="deal_amount_disclosed = BOOL",
        ),
    ],
)

BUSINESS_CONTRACT = CategoryRules(
    category="BUSINESS_CONTRACT",
    rules=[
        SubRule(
            id="bc_supply_contract_major",
            name="단일판매·공급계약 - 매출대비 50%+ & 상대방 명시",
            base=75, multiplier=1.2,
            llm_flag_required="counterparty_disclosed = true AND revenue_ratio >= 50%",
        ),
        SubRule(
            id="bc_supply_contract_minor",
            name="단일판매·공급계약 - 상대방 비공개 또는 매출대비 10% 미만",
            base=40, multiplier=0.6,
        ),
        SubRule(
            id="bc_free_issue",
            name="무상증자",
            base=70, multiplier=1.1,
        ),
    ],
)

EARNINGS = CategoryRules(
    category="EARNINGS",
    rules=[
        SubRule(
            id="er_turnaround",
            name="흑자전환",
            base=65, multiplier=1.2,
        ),
        SubRule(
            id="er_surprise",
            name="어닝 서프라이즈 (영업이익 컨센 대비 +30%↑)",
            base=50, multiplier=0.8,
        ),
        SubRule(
            id="er_loss_continued",
            name="적자지속/적자전환",
            base=25, multiplier=0.5,
        ),
    ],
)

SHAREHOLDER_RETURN = CategoryRules(
    category="SHAREHOLDER_RETURN",
    rules=[
        SubRule(
            id="sr_buyback_retirement",
            name="자사주 매입 후 소각",
            base=75, multiplier=1.2,
        ),
        SubRule(
            id="sr_buyback_only",
            name="단순 자사주 취득 결정",
            base=60, multiplier=1.0,
        ),
        SubRule(
            id="sr_major_holder_change_major",
            name="최대주주 변경 - 인수주체 대기업/유명펀드",
            base=70, multiplier=1.2,
            llm_flag_required="major_holder_acquirer_type = MAJOR_OR_FUND",
        ),
        SubRule(
            id="sr_major_holder_change_minor",
            name="최대주주 변경 - 인수주체 신생조합/비상장사",
            base=30, multiplier=0.5,
            llm_flag_required="major_holder_acquirer_type = NEW_ENTITY",
        ),
    ],
)

# Lookup map
_CATEGORY_MAP: Dict[str, CategoryRules] = {
    "CAPITAL_RAISING": CAPITAL_RAISING,
    "BIOTECH": BIOTECH,
    "BUSINESS_CONTRACT": BUSINESS_CONTRACT,
    "EARNINGS": EARNINGS,
    "SHAREHOLDER_RETURN": SHAREHOLDER_RETURN,
}


# ---------------------------------------------------------------------------
# Flag matching helpers
# ---------------------------------------------------------------------------

def _match_flag(rule: SubRule, flags: dict) -> bool:
    """Check if the given sub-rule's llm_flag_required matches the flags dict."""
    required = rule.llm_flag_required
    if required is None:
        return True  # no flag constraint — rule applies by default

    # Parse simple flag conditions
    # "third_party_target = CONGLOMERATE"
    # "deal_amount_disclosed = BOOL"
    # "counterparty_disclosed = true AND revenue_ratio >= 50%"
    # "cb_purpose = FACILITY_OR_ACQUISITION"
    # "major_holder_acquirer_type = MAJOR_OR_FUND"

    # Handle AND conditions
    if " AND " in required:
        parts = required.split(" AND ")
        return all(_eval_simple_condition(p.strip(), flags) for p in parts)

    return _eval_simple_condition(required, flags)


def _parse_condition_value(value: str) -> float:
    """Parse a condition value, stripping trailing % if present."""
    value = value.strip()
    if value.endswith("%"):
        value = value[:-1]
    return float(value)


def _eval_simple_condition(condition: str, flags: dict) -> bool:
    """Evaluate a single 'key = VALUE' or 'key >= value' condition."""
    # key = VALUE  (string equality or BOOL)
    if " = " in condition:
        key, value = condition.split(" = ", 1)
        key = key.strip()
        value = value.strip()

        # BOOL type — check existence and type
        if value == "BOOL":
            val = flags.get(key)
            return val is not None and isinstance(val, bool)

        # Boolean literal
        if value.lower() == "true":
            return flags.get(key) is True
        if value.lower() == "false":
            return flags.get(key) is False

        # String comparison
        return str(flags.get(key)) == value

    # key >= value
    if " >= " in condition:
        key, value = condition.split(" >= ", 1)
        key = key.strip()
        value = _parse_condition_value(value)
        flag_val = flags.get(key)
        if flag_val is None:
            return False
        return float(flag_val) >= value

    # key > value
    if " > " in condition:
        key, value = condition.split(" > ", 1)
        key = key.strip()
        value = _parse_condition_value(value)
        flag_val = flags.get(key)
        if flag_val is None:
            return False
        return float(flag_val) > value

    return False


def _eval_penalty_condition(condition: str, flags: dict) -> bool:
    """Evaluate a penalty condition string against flags."""
    # "payment_delay_days > 90"
    if " > " in condition:
        key, value = condition.split(" > ", 1)
        key = key.strip()
        value = float(value.strip())
        flag_val = flags.get(key)
        if flag_val is None:
            return False
        return float(flag_val) > value
    # "deal_amount_disclosed = false"
    if " = " in condition:
        key, value = condition.split(" = ", 1)
        key = key.strip()
        value = value.strip()
        if value.lower() == "false":
            return flags.get(key) is False
        if value.lower() == "true":
            return flags.get(key) is True
        return str(flags.get(key)) == value
    return False


def _evaluate_penalty(rule: SubRule, flags: dict) -> tuple:
    """Evaluate penalty condition. Returns (penalty_amount, use_override)."""
    if rule.penalty_condition is None:
        return 0, False

    condition_met = _eval_penalty_condition(rule.penalty_condition, flags)

    if not condition_met:
        return 0, False

    if rule.penalty_override_score is not None:
        return 0, True

    return rule.penalty or 0, False


# ---------------------------------------------------------------------------
# Main scoring API
# ---------------------------------------------------------------------------

def compute_score(category: str, sub_rule_flags: Optional[Dict[str, Any]] = None) -> ScoreResult:
    """
    Given a category (from LLM classification) and sub_rule_flags (from LLM),
    compute the DVI score deterministically.

    Returns ScoreResult with all derived fields.
    """
    if sub_rule_flags is None:
        sub_rule_flags = {}

    cat_rules = _CATEGORY_MAP.get(category)
    if cat_rules is None:
        return ScoreResult(
            dvi_score=0.0,
            sub_rule_id=None,
            impact_level="LOW_IMPACT",
            risk_flag="CAUTION",
            is_feed_visible=False,
        )

    # Two-phase matching:
    # Phase 1: Find a rule whose llm_flag_required is SATISFIED by the provided flags
    # Phase 2: Fall back to the first rule WITHOUT flag requirement
    matched_rule = None
    fallback_rule = None

    for rule in cat_rules.rules:
        if rule.llm_flag_required is None:
            if fallback_rule is None:
                fallback_rule = rule
            continue
        if _match_flag(rule, sub_rule_flags):
            matched_rule = rule
            break

    if matched_rule is None:
        matched_rule = fallback_rule

    if matched_rule is None:
        return ScoreResult(
            dvi_score=0.0,
            sub_rule_id=None,
            impact_level="LOW_IMPACT",
            risk_flag="CAUTION",
            is_feed_visible=False,
        )

    # Compute score
    penalty, use_override = _evaluate_penalty(matched_rule, sub_rule_flags)

    if use_override:
        raw_score = matched_rule.penalty_override_score
    else:
        raw_score = matched_rule.base * matched_rule.multiplier - penalty

    # Apply cap
    if matched_rule.score_cap is not None:
        raw_score = min(raw_score, matched_rule.score_cap)

    dvi_score = round(raw_score, 1)

    # Derive impact_level
    if dvi_score >= 80:
        impact_level = "HIGH_IMPACT"
    elif dvi_score >= 40:
        impact_level = "NORMAL"
    else:
        impact_level = "LOW_IMPACT"

    # Derive risk_flag
    if dvi_score < 20:
        risk_flag = "HIGH_RISK_TRAP"
    elif dvi_score < 40:
        risk_flag = "CAUTION"
    else:
        risk_flag = "CLEAN"

    # Feed visibility
    is_feed_visible = (dvi_score >= 70) or (risk_flag == "HIGH_RISK_TRAP")

    return ScoreResult(
        dvi_score=dvi_score,
        sub_rule_id=matched_rule.id,
        impact_level=impact_level,
        risk_flag=risk_flag,
        is_feed_visible=is_feed_visible,
    )


# ---------------------------------------------------------------------------
# Convenience: full pipeline (hard-fail check → score)
# ---------------------------------------------------------------------------

def evaluate_disclosure(raw_text: str, category: str,
                        sub_rule_flags: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Full pipeline: check hard-fail first, then compute score.
    Returns dict ready to insert into Supabase.
    """
    # 1. Hard-fail check
    hard_fail = check_hard_fail(raw_text)
    if hard_fail.detected:
        return {
            "dvi_score": 0.0,
            "sub_rule_id": None,
            "impact_level": "LOW_IMPACT",
            "risk_flag": "HIGH_RISK_TRAP",
            "is_feed_visible": True,
            "skip_llm": True,
            "deceptive_pattern_detected": True,
            "momentum_authenticity": "LOW",
        }

    # 2. Normal scoring
    result = compute_score(category, sub_rule_flags)
    return {
        "dvi_score": result.dvi_score,
        "sub_rule_id": result.sub_rule_id,
        "impact_level": result.impact_level,
        "risk_flag": result.risk_flag,
        "is_feed_visible": result.is_feed_visible,
        "skip_llm": False,
        "deceptive_pattern_detected": None,
        "momentum_authenticity": None,
    }
