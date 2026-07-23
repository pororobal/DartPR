"""Unit tests for hard-fail detection."""

from app.services.rules_engine import check_hard_fail


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
