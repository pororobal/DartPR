"""Unit tests for rules engine — hard-fail, signal_horizon, ambiguous titles."""

from app.services.rules_engine import (
    check_hard_fail,
    _assign_signal_horizon,
    _is_ambiguous_title,
)


class TestHardFail:
    def test_clean_text_no_fail(self):
        result = check_hard_fail("삼성전자가 시설자금 조달을 위해 유상증자를 결정")
        assert result.detected is False

    def test_hard_fail_감사의견거절(self):
        result = check_hard_fail("감사의견거절로 인한 상장폐지 사유 발생")
        assert result.detected is True
        assert result.matched_keyword == "감사의견거절"

    def test_hard_fail_횡령(self):
        result = check_hard_fail("전 대표의 횡령 사실이 확인됨")
        assert result.detected is True
        assert result.matched_keyword == "횡령"

    def test_hard_fail_배임(self):
        result = check_hard_fail("배임 혐의로 검찰 수사 중")
        assert result.detected is True

    def test_hard_fail_감자(self):
        result = check_hard_fail("감자 결정 공시")
        assert result.detected is True

    def test_hard_fail_상장폐지(self):
        result = check_hard_fail("상장폐지 사유 해당")
        assert result.detected is True

    def test_hard_fail_all_keywords(self):
        assert check_hard_fail("감사의견한정").detected is True
        assert check_hard_fail("감사의견부적정").detected is True


class TestSignalHorizon:
    def test_earnings_rule_returns_short_term(self):
        assert _assign_signal_horizon("EARNINGS_REVENUE_INCREASE", "EARNINGS") == "SHORT_TERM"
        assert _assign_signal_horizon("EARNINGS_LOSS_TO_PROFIT_NO_HISTORY", "EARNINGS") == "SHORT_TERM"
        assert _assign_signal_horizon("EARNINGS_OP_PROFIT_WORSENING", "EARNINGS") == "SHORT_TERM"

    def test_biotech_fda_returns_long_term(self):
        assert _assign_signal_horizon("BIOTECH_FDA_APPROVAL", "BIOTECH") == "LONG_TERM"
        assert _assign_signal_horizon("BIOTECH_PHASE3_NDA", "BIOTECH") == "LONG_TERM"

    def test_biotech_negative_returns_short_term(self):
        assert _assign_signal_horizon("BIOTECH_CLINICAL_HOLD", "BIOTECH") == "SHORT_TERM"
        assert _assign_signal_horizon("BIOTECH_TECH_RETURN", "BIOTECH") == "SHORT_TERM"

    def test_ma_merger_returns_long_term(self):
        assert _assign_signal_horizon("MA_MERGER", "MA") == "LONG_TERM"
        assert _assign_signal_horizon("MA_OVERSEAS_LISTING", "MA") == "LONG_TERM"
        assert _assign_signal_horizon("MA_ACTIVIST", "MA") == "LONG_TERM"

    def test_shareholder_return_short_term(self):
        assert _assign_signal_horizon("SHAREHOLDER_BUYBACK_ONLY", "SHAREHOLDER_RETURN") == "SHORT_TERM"
        assert _assign_signal_horizon("SHAREHOLDER_DISPOSAL_OPERATING", "SHAREHOLDER_RETURN") == "SHORT_TERM"

    def test_business_contract_category_fallback(self):
        assert _assign_signal_horizon("", "BUSINESS_CONTRACT") == "SHORT_TERM"

    def test_earnings_category_fallback(self):
        assert _assign_signal_horizon("", "EARNINGS") == "SHORT_TERM"

    def test_capital_raising_category_fallback(self):
        assert _assign_signal_horizon("", "CAPITAL_RAISING") == "SHORT_TERM"

    def test_administrative_returns_empty(self):
        assert _assign_signal_horizon("", "ADMINISTRATIVE") == ""
        assert _assign_signal_horizon("SOME_UNKNOWN_RULE", "OTHER") == ""


class TestAmbiguousTitle:
    def test_ambiguous_신규시설투자(self):
        assert _is_ambiguous_title("신규시설 투자 결정") is True

    def test_ambiguous_풍문해명(self):
        assert _is_ambiguous_title("풍문또는보도에 대한 해명 공시") is True

    def test_ambiguous_증권신고서(self):
        assert _is_ambiguous_title("증권신고서 제출") is True

    def test_ambiguous_채무보증(self):
        assert _is_ambiguous_title("채무보증 결정 공시") is True

    def test_ambiguous_대표이사변경(self):
        assert _is_ambiguous_title("대표이사 변경") is True

    def test_ambiguous_조회공시(self):
        assert _is_ambiguous_title("조회공시 답변") is True
        assert _is_ambiguous_title("조회공시 확정") is True

    def test_not_ambiguous_자사주(self):
        assert _is_ambiguous_title("자사주 취득 결정") is False

    def test_not_ambiguous_FDA(self):
        assert _is_ambiguous_title("FDA 품목허가 승인") is False

    def test_not_ambiguous_empty(self):
        assert _is_ambiguous_title("") is False
