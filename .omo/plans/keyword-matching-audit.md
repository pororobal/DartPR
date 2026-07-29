# 키워드 매칭 전수 점검 및 개선 제안안

> 분석 기준: `rules_engine.py` (1473행) — `_extract_keywords()`, `guess_category()`, `_score_*()`, `evaluate_disclosure()`, `check_*()` 전함수  
> 검증 데이터: 2026-07-27 DART 공시 399건 + 사용자 피드백

---

## 🔴 0순위 — 카테고리 라우팅 불일치 (구조적 버그)

### 문제
`guess_category()`가 "OTHER"를 반환하면 `_route_category_scoring("OTHER")`는 **무조건 DVI 30**을 반환한다.
→ `_score_shareholder_ma()`의 22개 sub_rule 중 **12개가 영영 실행되지 않는다.**

### 영향받는 scoring 로직 (죽은 코드)

| `_score_shareholder_ma()` 패턴 | 예상 DVI | `guess_category()` 매칭 여부 | 현재 결과 |
|---|---|---|---|
| `block_trade` (장내매도) | 6 | ❌ | OTHER → DVI 30 |
| `equity_acquisition` (타법인지분양수) | 55 | ❌ | OTHER → DVI 30 |
| `overseas_listing` (해외상장) | 60 | ❌ | OTHER → DVI 30 |
| `egm_called` (임시주주총회) | 50 | ❌ | OTHER → DVI 30 |
| `ceo_changed` (대표이사변경) | 45 | ❌ | OTHER → DVI 30 |
| `proxy_fight` (위임장대결) | 75 | ❌ | OTHER → DVI 30 |
| `shareholder_proposal` (주주제안) | 60 | ❌ | OTHER → DVI 30 |
| `activist_detected` (행동주의) | 70 | ❌ | OTHER → DVI 30 |
| `collateral_provision` (담보제공) | 15 | ❌ | OTHER → DVI 30 |
| `debt_to_equity` (출자전환) | 5 | ❌ | OTHER → DVI 30 |
| `debt_forgiveness` (채무면제) | 3 | ❌ | OTHER → DVI 30 |
| `business_transfer` (영업양수도) | 55 | ❌ | OTHER → DVI 30 |
| `share_exchange` (주식교환) | 55 | ❌ | OTHER → DVI 30 |
| `auditor_changed` (감사인변경) | 30 | ❌ | OTHER → DVI 30 |

### 실사례
- `타법인주식및출자증권취득결정(자율공시)` → 엠아이텍 11:27
  - 현재: `guess_category()` → "OTHER" → DVI 30
  - 정상: `_score_shareholder_ma()` → `equity_acquisition` → DVI 55
- `대표이사(대표집행임원)변경(안내공시)` → 주연테크
  - 현재: "OTHER" → DVI 30
  - 정상: `_score_shareholder_ma()` → `ceo_changed` → DVI 45

### 수정안
**Option A (근본해결)**: `_route_category_scoring()`에서 "OTHER"도 `_score_shareholder_ma()`를 통과시킨 후, 결과가 MA_GENERAL(기본값 30)이면 DVI 30 반환.

```python
def _route_category_scoring(category, keywords, ticker, supabase):
    ...
    # OTHER → M&A scorer 먼저 시도 (낙아웃)
    if category == "OTHER":
        ma_s, ma_sid, risk, st = _score_shareholder_ma(keywords, ticker, supabase)
        if ma_sid != "MA_GENERAL":  # 실제 매칭된 경우만 반환
            return {"score": ma_s, "sub_id": ma_sid, "risk_flag": risk, "sub_type": st}
        return {"score": 30, "sub_id": "OTHER_DEFAULT"}
```

**Option B (보수적)**: `guess_category()`에 누락된 패턴 14개 추가.
→ 단순하지만 `guess_category()`가 커짐. 유지보수 어려움.

**추천: Option A + Option B 병용** — A로 근본 해결, B로 1차 분류 정확도 향상.

---

## 🔴 0순위 — CB 순서 의존성 버그 (P0, 1행 수정)

### 문제
```python
# 751행 (먼저 체크)
if keywords.get("cb_conversion_exercised"):
    return (8, ...)  # 부정

# 755행 (나중 체크)
if keywords.get("cb_early_redemption"):
    return (65, ...)  # 긍정
```

"자기전환사채만기전취득결정" = 회사가 자기 CB를 사들임 = **긍정**.
그런데 "전환" 문자열이 `cb_conversion_exercised`를 트리거하면 DVI 8(부정)으로 왜곡됨.

### 영향
- 모아데이타 `자기전환사채만기전취득` DVI 8 (실제론 DVI 65)

### 수정
```python
# CB 조기상환/만기전취득을 먼저 체크 (긍정 우선)
if keywords.get("cb_early_redemption"):
    return (65, "CAPITAL_RAISING_CB_EARLY_REDEEM", "", "")
# CB 전환청구 — 이후 체크
if keywords.get("cb_conversion_exercised"):
    return (8, "CAPITAL_RAISING_CB_CONVERTED", "", "")
```

---

## 🔴 0순위 — "전환가액의조정" 리픽싱 미검출 (P0, 1행 수정)

### 문제
```python
# 159행
r"(전환가액\s*조정|리픽싱|전환가액\s*하향)"
```
- "전환가액**의**조정" → `의`가 `\s*`(공백만 매칭)와 안 맞음 → `cb_refixing` = False
- 실제 리픽싱(부정, DVI 5)인데 DVI 30으로 fallback

### 수정
```python
r"(전환가액의?\s*조정|리픽싱|전환가액\s*하향)"
# 또는
r"(전환가액\S*조정|리픽싱|전환가액\s*하향)"
```

---

## 🟡 1순위 — 키워드/스코어링 갭

### ④ 잠정실적 수치 미추출 → DVI 30

**문제**: `연결재무제표기준영업(잠정)실적(공정공시)` — title에 "실적" 포함.
`_score_earnings()`가 `revenue_amount`, `operating_profit_positive` 등을 추출하는데,
raw_text[:3000]에 숫자가 없으면 키워드 미추출 → DVI 30 `EARNINGS_GENERAL`.

**영향**: 기업은행, 한솔테크닉스, 삼성카드 등 20+ 공시 (5%+)

**수정 ④-a**: title에 "잠정실적" 있으면 최소 DVI 40 보장
```python
# _score_earnings() 마지막 return 직전
if keywords.get("preliminary_earnings", False):
    return (40, "EARNINGS_PRELIMINARY", "", "잠정실적")
return (30, "EARNINGS_GENERAL", "", "일반실적")
```

**수정 ④-b**: `_extract_keywords()`에서 숫자 추출 regex 강화
- 현재: `r"(매출액|매출).*?(\d[\d,]*)\s*(억|원)"` — "매출" 뒤 숫자
- 개선안: `r"(매출액|영업이익|당기순이익).*?(\d[\d,]*)\s*(억|원)"` — 영업이익/순이익도 추출

---

### ⑤ `(자율공시)` 보너스 미적용

**문제**:
```python
# 1377행
if "[자율공시]" in title:  # 대괄호만 체크
    voluntary_bonus = 10
```
실제 제목: `타법인주식및출자증권취득결정(자율공시)` — 소괄호.

**영향**: 엠아이텍(11:27), 에이프로젠(13:20), 대동기어(10:46) 등 +10 못 받음

**수정**:
```python
if "[자율공시]" in title or "(자율공시)" in title:
    voluntary_bonus = 10
```

---

### ⑥ `check_hard_fail()` — 정정공시 오탐 위험

**문제**:
```python
def check_hard_fail(raw_text: str):
    for kw in HARD_FAIL_KEYWORDS:
        if kw in raw_text:  # raw_text 전체에서 검색
            return HardFailResult(detected=True, ...)
```
`[기재정정]회생절차개시결정` — 본문에 "회생절차"가 있으면 FAST-FAIL.
하지만 **정정공시**는 "이전에 보고한 회생절차 건에 대한 정정"일 뿐,
실제 회생절차가 새로 발생한 게 아님.

**영향**: 범양건영(10:32) `[기재정정]회생절차개시결정`

**수정**:
```python
if "[기재정정]" in title:
    return HardFailResult(detected=False)  # 정정공시는 skip
```
→ 단, 정정공시 중에도 실제 위험을 보고하는 케이스(예: 횡령 정정)는 있을 수 있어서
트레이드오프. 아래가 더 안전:
```python
# "기재정정"이면 HARD_FAIL 강도 낮춤 (0→20점, skip_llm 해제)
```

---

### ⑦ 중대재해 미분류

**문제**: "중대재해" 관련 키워드가 `_extract_keywords()`와 `guess_category()`에 없음.
- HD현대 `중대재해발생(종속회사의주요경영사항)` (08:35)
- HD한국조선해양 `중대재해발생(자회사의 주요경영사항)` (07:47)
- HD현대중공업 `중대재해발생` (07:45)
→ 모두 "OTHER" → DVI 30

**수정**: `_extract_keywords()`에 `serious_accident` 플래그 추가 + `_score_shareholder_ma()`에 DVI 10 할당.

---

### ⑧ 대량보유보고서 → "주주환원" 오분류

**문제**: `guess_category()` 573행
```python
if any(kw in t for kw in ["대량보유", "주식등의대량보유", "지분"]):
    return ("SHAREHOLDER_RETURN", keywords)
```
대량보유보고서(5%룰) = 단순 지분변동 보고 ≠ 주주환원 정책.

**영향**: 한국항공우주(약식), 소프트캠프(일반) 등 — "주주환원" 태그 UX 혼란

**수정**: 
```python
if any(kw in t for kw in ["대량보유", "주식등의대량보유"]):
    return ("OTHER", keywords)  # SHAREHOLDER_RETURN → OTHER
```
→ 단, `_score_shareholder_ma()`의 `bulk_holding_management`(경영참여 목적, DVI 65)는
SHAREHOLDER_RETURN으로 유지되어야 함.
→ 따라서 키워드를 분리: "대량보유+경영참여"만 SHAREHOLDER_RETURN, 나머지는 OTHER.

---

### ⑨ 행정 패턴 갭 — "특수관계인과의수익증권거래"

**문제**: `_ADMIN_PATTERNS`에 `"특수관계인과의거래"`가 있지만
실제 제목은 `특수관계인과의수익증권거래` (수익증권이 사이에 끼어있음).
→ `stripped in t` 체크에서 미매칭 → OTHER → DVI 30.

**영향**: 삼성에스알에이자산운용(13:08, 13:09) 특수관계인과의수익증권거래 2건

**수정**:
```python
_ADMIN_PATTERNS.append("특수관계인과의")  # 접두사 매칭으로 완화
```
또는 regex 패턴으로 변경.

---

### ⑩ 주식병합결정 미분류

**문제**: `guess_category()`에 "병합" 없음 ("합병"만 있음).
- 덕신이피씨 `[기재정정]주식병합결정` (16:47)
- 액면병합 = 주식 수 감소 → CAPITAL_RAISING(유상감자) or SHAREHOLDER_RETURN

**수정**: `guess_category()`에 `"병합"` 추가 → SHAREHOLDER_RETURN or CAPITAL_RAISING.

---

## 🟢 2순위 — 개선 권장

### ⑪ 비유동자산취득결정 미분류

- 행복모아(13:10) `비유동자산취득결정`
- "비유동자산" = 부동산/설비 취득 → CAPITAL_RAISING(시설자금 성격) or SHAREHOLDER_RETURN
- 현재: OTHER → DVI 30

### ⑫ 특수관계인에대한자금대여 미분류

- 에이케이아이에스(13:14) `특수관계인에대한자금대여`
- 특수관계인 자금대여 = 지배구조 리스크 → `_score_shareholder_ma()`에서 DVI 15~20
- 현재: OTHER → DVI 30

### ⑬ 지급수단별 지급금액 공시 행정 처리

- 에피톤코리아, 포스코에어솔루션 등 (10+건)
- 대부업체/캐피탈 정기 보고. 행정 성격.
- `_ADMIN_PATTERNS`에 패턴 추가 권장

### ⑭ 투자설명서(일괄신고) 모호 분석 비용

- `_is_ambiguous_title()`에 "투자설명서"가 있음
- 근데 `guess_category()`가 ADMINISTRATIVE로 보냄
- `evaluate_disclosure()` 1418행:
  ```python
  ambiguous = _is_ambiguous_title(title) and category in ("OTHER", "ADMINISTRATIVE")
  ```
- category가 ADMINISTRATIVE면 → `needs_cerebras=True` → 모호 분석 비용 발생 + skip_llm=True
- 비효율적. ADMINISTRATIVE는 `_is_ambiguous_title` 체크에서 제외.

---

### 요약: 수정 공수 대비 효과

| 순위 | 항목 | 수정량 | 영향 공시 수 (399건 기준) | 난이도 |
|:---:|:----:|:------:|:-------------------------:|:------:|
| ① | 카테고리 라우팅 | **+5행** | ~30건 | 중 |
| ② | CB 순서 | **1행** | ~3건 | 하 |
| ③ | 리픽싱 regex | **1행** | ~5건 | 하 |
| ④ | 잠정실적 보너스 | **3행** | ~20건 | 하 |
| ⑤ | 자율공시 괄호 | **1행** | ~5건 | 하 |
| ⑥ | 정정 HARD_FAIL | **3행** | ~3건 | 중 |
| ⑦ | 중대재해 | **5행** | ~3건 | 하 |
| ⑧ | 대량보유 카테고리 | **3행** | ~15건 | 중 |
| ⑨ | 행정 패턴 | **1행** | ~10건 | 하 |
| ⑩ | 주식병합 | **1행** | ~2건 | 하 |
| ⑪~⑬ | 기타 갭 | **10행** | ~15건 | 하~중 |

**①+②+③+④+⑤만 해도 399건 중 ~60건(15%) 분류 정확도 개선.**
변경량은 단 11행. 공수 대비 효과 가장 높음.

진행할까?
