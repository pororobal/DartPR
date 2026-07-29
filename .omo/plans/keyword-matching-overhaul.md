# DVI 키워드 매칭 전면 개선 계획

> 분석 기준: `rules_engine.py` 1,473행 전함수, 399건 실제 DART 공시  
> 분석 모드: 애널리스트 빙의 — 키워드만으로 판단 가능한 것과 불가능한 것을 엄격히 분리

---

## 목차
1. [P0: 즉시 수정 — 구조적 버그 3건](#1-p0-즉시-수정--구조적-버그-3건)
2. [P1: 키워드 패턴 보강 (9행)](#2-p1-키워드-패턴-보강-9행)
3. [P2: Groq 라우팅 개선 (핵심)](#3-p2-groq-라우팅-개선-핵심)
4. [P3: 카테고리 라우팅 개선](#4-p3-카테고리-라우팅-개선)
5. [P4: 수치 정규화 로직](#5-p4-수치-정규화-로직)
6. [P5: 모니터링/검증](#6-p5-모니터링검증)
7. [실행 우선순위 및 예상 효과](#7-실행-우선순위-및-예상-효과)

---

## 1. P0: 즉시 수정 — 구조적 버그 3건

### 1-a. CB 순서 역전 (1행)

**파일**: `rules_engine.py` 750~756행  
**문제**: `cb_conversion_exercised`(DVI 8)가 `cb_early_redemption`(DVI 65)보다 먼저 체크됨.  
→ "자기전환사채만기전취득"에 "전환"이 포함되어 있어 부정(DVI 8)으로 잘못 분류.

**수정**:
```python
# CB 조기상환/만기전취득을 먼저 체크 (긍정 우선)
if keywords.get("cb_early_redemption"):
    return (65, "CAPITAL_RAISING_CB_EARLY_REDEEM", "", "")
# CB 전환청구 — 이후 체크
if keywords.get("cb_conversion_exercised"):
    return (8, "CAPITAL_RAISING_CB_CONVERTED", "", "")
```

**영향**: 모아데이타 등 자기CB 취득 공시 DVI 8→65

---

### 1-b. "전환가액의조정" 리픽싱 미검출 (1행)

**파일**: `rules_engine.py` 158행  
**문제**: `r"(전환가액\s*조정|리픽싱|전환가액\s*하향)"` — `\s*`가 공백만 매칭, `의`는 미매칭.

**수정**:
```python
flags["cb_refixing"] = bool(
    re.search(r"(전환가액\S{0,3}조정|리픽싱|전환가액\s*하향)", text)
)
```

> **참고**: `\S*`→`\S{0,3}`으로 제한. `\S*`는 탐욕적이라 "전환가액 관련 세부사항은 별도 조정" 같은 문장까지 매칭될 수 있음.  
> 실제 "전환가액의조정"에서 "의"는 1글자이므로 `{0,3}`이면 충분히 커버되고 오탐 위험은 낮아짐.

**영향**: 뷰티스킨 등 리픽싱 공시 DVI 30→5

---

### 1-c. `check_administrative()`가 `[기재정정]`을 못 잡음 (1행)

**파일**: `rules_engine.py` 73~93행  
**문제**: 
```python
_ADMIN_PATTERNS = [
    ...
    "정정신고",   # DART 리포트 타입 (제목에 없음)
    # "기재정정"이 없음 ← 제목에 붙는 접두사
]
```
→ `[기재정정]단일판매ㆍ공급계약체결` → "정정신고" is NOT in title → `check_administrative` False.

**수정**:
```python
_ADMIN_PATTERNS = [
    ...
    "기재정정",   # ← 추가
    "정정신고",
    ...
]
```

**영향**: BHI 등 계약기간 연장 정정공시 DVI 15→10

---

## 2. P1: 키워드 패턴 보강 (9행)

### 2-a. 자율공시 소괄호 (1행)

```python
# rules_engine.py 1377행
if "[자율공시]" in title or "(자율공시)" in title:
    voluntary_bonus = 10
```

**영향**: 엠아이텍, 에이프로젠 등 (자율공시) 형식 +10 보너스

---

### 2-b. "주식병합" → SHAREHOLDER_RETURN (1행)

```python
# guess_category()에 추가
if any(kw in t for kw in ["주식병합"]):
    return ("SHAREHOLDER_RETURN", keywords)
```

**영향**: 덕신이피씨 등 액면병합 DVI 30→45

---

### 2-c. "중대재해" → DELISTING_RISK (우회) + 위험 플래그 (3행)

```python
# _extract_keywords()에 추가
flags["serious_accident"] = bool(re.search(r"중대재해", text))

# evaluate_disclosure()에 추가 (risk 체크 섹션)
if keywords.get("serious_accident"):
    return ScoreResult(
        category="DELISTING_RISK",
        sub_rule_id="RISK_SERIOUS_ACCIDENT",
        dvi_score=10,
        impact_level="HIGH_IMPACT",
        is_feed_visible=True,
        skip_llm=False,           # ← 요약 필요 (사망/경상 등 편차 큼)
        signal_horizon="SHORT_TERM",
    )
```

> **참고**: `skip_llm=False`로 설정. 중대재해 내에서도 사망사고 vs 경상사고 등 편차가 있으므로  
> Groq 요약이 있어야 사용자가 "뭐가 얼마나 중대한지" 판단 가능.

**영향**: HD현대 3사 중대재해 DVI 30→10

---

### 2-d. "비유동자산취득" → CAPITAL_RAISING (1행)

```python
# guess_category()에 추가
if any(kw in t for kw in ["비유동자산취득"]):
    return ("CAPITAL_RAISING", keywords)
```

**영향**: 행복모아 등 자산취득 DVI 30→30 (카테고리만 개선, 점수는 GR로)

---

### 2-e. "특수관계인과의" 접두사 ADMIN 매칭 완화 (1행)

```python
# 기존 "특수관계인과의거래" 외에 접두사 매칭
_ADMIN_PATTERNS.append("특수관계인과의")
```

**영향**: 특수관계인과의수익증권거래 등 DVI 30→10

---

### 2-f. 매출액대비(%) 정규식 보강 (1행)

```python
# 231행 — 현재
m = re.search(r"(최근\s*매출액\s*대비|매출액\s*대비).*?(\d+(?:\.\d+)?)", text)
# 개선
m = re.search(r"(최근\s*매출액\s*대비|매출액\s*대비|매출액대비).*?(\d+(?:\.\d+)?)", text)
```

**영향**: BHI 정정공시에서 revenue_ratio=19.6 추출 → DVI 15→50

---

## 3. P2: Groq 라우팅 개선 (핵심)

### 3-a. 문제 인식: 30~59점 사각지대

```
현재 구조:
  score < 60  → skip_llm=True (Groq 분석 없음)  ← 30~59점 = 가장 애매한 구간
  score >= 60 → skip_llm=False (Groq 요약)
```

**30~59점 구간에 어떤 것들이 몰리는가** (Failure Mode B, E, F):

| 점수 | 유형 | 예시 |
|:---:|:----|:----|
| 30 | OTHER 기본값 | `기타경영사항`, `특수관계인자금대여`, `비유동자산취득` |
| 30 | CAPITAL_RAISING_GENERAL | CB/BW 발행(자금목적 미추출) |
| 30 | EARNINGS_GENERAL | 잠정실적(수치 미추출) |
| 30 | SHAREHOLDER_GENERAL | 공정공시, 조회공시답변 |
| 30 | MA_GENERAL → SH_GENERAL | 지분공시, 주주총회소집 |
| 30 | BIOTECH_GENERAL | 임상 중간 결과 |
| 45 | CAPITAL_RAISING_THIRD_PARTY_GENERAL | 제3자배정(대상자 일반) |
| 48~54 | SHAREHOLDER_BUYBACK/DIVIDEND | 자사주취득/배당(규모 미확인) |
| 55 | MA_EQUITY_ACQUISITION | 타법인지분양수(규모 미확인) |

> **핵심 인사이트**: 30점은 "키워드 매칭 실패"의 신호이고, 30~55점은 "키워드는 매칭됐지만 수치/맥락이 없어서 확신 불가"의 신호다. 모두 LLM 재평가가 필요한 구간.

---

### 3-b. 개선안: 3단계 LLM 라우팅

> **순서 의존성 주의**: Phase 2(4-a)에서 OTHER→M&A/SH reroute가 먼저 적용된 후  
> `_needs_llm()`이 실행됨. 따라서 `_needs_llm`이 받는 `category`는 이미 reroute 후의 값.  
> reroute 성공 = MA_*/SH_* → `_needs_llm` 통과.  
> reroute 실패 = `OTHER_DEFAULT` fallback → LLM 필요.  
> → `category == "OTHER"` 대신 `sub_rule_id == "OTHER_DEFAULT"`로 체크해야 정확.

```python
def _needs_llm(score: int, category: str, sub_rule_id: str, title: str, keywords: dict) -> bool:
    """LLM 분석이 필요한지 결정.

    실행 시점: Phase 2 카테고리 reroute(4-a) 이후.
    - reroute 성공 → 이미 MA_*/SH_*로 재분류됨
    - reroute 실패 → sub_rule_id == "OTHER_DEFAULT" (진짜 키워드 미매칭)
    """
    
    # (1) 규칙 기반으로 충분한 케이스 = skip LLM
    if score < 30:
        return False  # 0~29점: HARD_FAIL, ADMIN, 저신뢰 — 규칙 기반 확정
    if sub_rule_id in ("DELISTING_RISK",):
        return False  # 상장폐지 위험 — 규칙으로 충분
    if "[기재정정]" in title:
        return False  # 정정공시 — 규칙으로 충분 (일단)
    
    # (2) 모호 제목 — 무조건 LLM (기존 유지)
    if _is_ambiguous_title(title):
        return True
    
    # (3) 30~59점 구간 — 카테고리/서브타입별 차등
    if 30 <= score <= 59:
        # sub_rule_id == "OTHER_DEFAULT" = 4-a reroute도 실패 = 진짜 미분류
        if sub_rule_id == "OTHER_DEFAULT":
            return True
        # BUSINESS_CONTRACT with revenue_ratio unknown → LLM (NEW)
        if category == "BUSINESS_CONTRACT" and "revenue_ratio" not in keywords:
            return True
        # CAPITAL_RAISING with no cb_purpose → LLM (NEW)
        if category == "CAPITAL_RAISING" and sub_rule_id == "CAPITAL_RAISING_GENERAL":
            return True
        # LLM 기본값: skip (비용 절감)
        return False
    
    # (4) 60+ — 요약용 LLM (기존 유지)
    return True
```

> **⚠️ 중요 버그**: 초기안에 `if score <= 10: return False`만 있었음 → 11~29점이 마지막 `return True`로 누수.  
> `if score < 30: return False`로 수정해서 0~29 전 구간 차단.  
> 이 버그가 있으면 LLM 비용이 예상(+37.5%)보다 **~70% 증가**할 수 있음.  
>
> **순서 의존성 해결**: `category == "OTHER"`는 Phase 2 reroute 후에는 의미 없음.  
> reroute가 실패해서 남는 `OTHER_DEFAULT`로 체크해야 정확.  
> reroute 성공 건은 MA_*/SH_*로 `_needs_llm`에 들어오므로 문제 없음.

### 3-c. 예상 Groq 비용 변화

> **11~29 누수 수정 반영**: 0~29 전 구역 Skip LLM 확정.  
> 30~59 중에서도 `sub_rule_id == "OTHER_DEFAULT"`,  
> `BUSINESS_CONTRACT(ratio unknown)`, `CAPITAL_RAISING_GENERAL`만 LLM → 약 10%p 추가.

| 구간 | 현재 | 개선 후 | 비용 증감 |
|:---:|:---:|:-------:|:--------:|
| 0~29 (25%) | Skip LLM | Skip LLM | 동일 |
| 30~59 (40%) | Skip LLM | **선별적 LLM** (~10%p) | **+28%** |
| 60~79 (25%) | 짧은 요약 | 짧은 요약 | 동일 |
| 80~100 (10%) | 전체 요약 | 전체 요약 | 동일 |
| **합계** | **35%** | **~45%** | **+28%** |

**순증**: 기존 대비 약 **28% 토큰 증가** (11~29 누수 수정 전 37.5%보다 낮음)  
**상쇄 방안**: max_tokens 1200→600 (짧은 요청), 모호 400→300, Groq 모델 효율화로  
실질 비용 증가 10~15%로 억제 가능.

---

## 4. P3: 카테고리 라우팅 개선

### 4-a. "OTHER"도 M&A 스코어러 통과 (3행)

```python
# _route_category_scoring() 1470행 이후
# OTHER → M&A scorer 먼저 시도
if category == "OTHER":
    ma_s, ma_sid, risk, st = _score_shareholder_ma(keywords, ticker, supabase)
    if ma_sid != "MA_GENERAL":  # 실제 매칭된 경우
        return {"score": ma_s, "sub_id": ma_sid, "risk_flag": risk, "sub_type": st}
    # OTHER + shareholder_return도 시도
    sh_s, sh_sid, risk, st = _score_shareholder_return(keywords, ticker, supabase)
    if sh_sid != "SHAREHOLDER_GENERAL":
        return {"score": sh_s, "sub_id": sh_sid, "risk_flag": risk, "sub_type": st}
    return {"score": 30, "sub_id": "OTHER_DEFAULT"}
```

**영향**:  
- `대량보유보고서(단순투자)` → OTHER → MA_BULK_HOLDING_INVESTMENT DVI 12  
- `대표이사변경` → OTHER → MA_CEO_CHANGED DVI 45  
- `출자전환` → OTHER → MA_DEBT_TO_EQUITY DVI 5  
- `채무면제` → OTHER → MA_DEBT_FORGIVENESS DVI 3  
- `영업양수도` → OTHER → MA_BUSINESS_TRANSFER DVI 55  
- `주식교환` → OTHER → MA_SHARE_EXCHANGE DVI 55  
- `담보제공` → OTHER → MA_COLLATERAL_PROVISION DVI 15  
- `해외상장` → OTHER → MA_OVERSEAS_LISTING DVI 60  
- `임시주주총회소집` → OTHER → MA_EGM_GENERAL DVI 50  
- `행동주의펀드등장` → OTHER → MA_ACTIVIST DVI 70

→ **10개 패턴 DVI 30→정상 점수로 복귀** (단 3행 수정)

---

### 4-b. 대량보유보고서 → "OTHER"로 전환 (3행)

```python
# guess_category() 573행 — 기존
if any(kw in t for kw in ["대량보유", "주식등의대량보유", "지분"]):
    return ("SHAREHOLDER_RETURN", keywords)

# 개선
if any(kw in t for kw in ["주식등의대량보유", "대량보유"]):
    return ("OTHER", keywords)  # → 4-a를 통해 MA_BULK_HOLDING_*로 라우팅
if "지분" in t:
    # M&A 성격이면 SHAREHOLDER_RETURN, 단순 보고면 OTHER
    return ("SHAREHOLDER_RETURN", keywords)
```

**영향**: 한국항공우주 등 단순 대량보유가 "주주환원" 카테고리로 잘못 분류되는 문제 해결

---

## 5. P4: 수치 정규화 로직

### 5-a. 시가총액 대비 증자 규모 평가

현재: 유상증자 금액 추출 → 금액 크기로만 점수 산정  
개선: 증자금액 / 시총(DB 조회) 비율로 점수 조정

```python
# _score_capital_raising()에 추가
def _adjust_by_market_cap(base_score, raise_amount, ticker, supabase):
    """시총 대비 증자 규모로 점수 조정."""
    if not supabase or not ticker or not raise_amount:
        return base_score
    try:
        market_cap = _get_market_cap(supabase, ticker)  # 신규 함수
        if market_cap and market_cap > 0:
            ratio = raise_amount / market_cap
            if ratio >= 0.5:       # 시총 50% 이상 = 대규모
                return base_score + 10
            elif ratio >= 0.2:     # 시총 20% 이상 = 중규모
                return base_score + 5
            elif ratio <= 0.02:    # 시총 2% 미만 = 소규모
                return base_score - 10
    except Exception:
        pass
    return base_score
```

**공수**: ~15행, DB 스키마 변경 필요 (market_cap 정보)

> **⚠️ 단위 검증 필수**: `ratio = raise_amount / market_cap` — `raise_amount`가  
> 어떤 단위인지(원 / 억원 / 백만원) 먼저 확인해야 함.  
> DART 원문 수치 추출 로직(`_score_capital_raising` 이전 단계)이  
> 정규화하는 단위와 `market_cap` DB 컬럼의 단위가 일치하지 않으면  
> 비율이 자릿수 단위로 틀어짐.  
> **적용 전에 `revenue_amount`, `contract_amount`, `cancel_shares` 등  
> 수치 추출 함수들의 단위를 전수 확인할 것.**

---

## 6. P5: 모니터링/검증

### 6-a. 규칙 기반 vs LLM 분석 비교 대시보드

```sql
-- Supabase에 추가할 로그 테이블
CREATE TABLE scoring_audit (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    disclosure_id TEXT,
    title TEXT,
    rule_score INT,
    llm_score INT,        -- Groq이 평가한 점수
    rule_category TEXT,
    llm_category TEXT,    -- Groq이 분류한 카테고리
    llm_summary TEXT,
    discrepancy INT,      -- rule_score - llm_score
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

30~59점 구간에서 rule_score ≠ llm_score인 케이스를 주기적으로 리뷰.

### 6-b. 정기 감사

- 격주 1회: 최근 2주간 30~59점 DVI의 LLM 재평가 결과 리뷰
- 새로운 패턴 발견 시 guess_category() / _ADMIN_PATTERNS에 반영

---

## 7. 실행 우선순위 및 예상 효과

### Phase 1: 즉시 적용 (당일, 위험도 낮음)

| 순서 | 항목 | 수정량 | 영향 공시 | 효과 |
|:---:|:----|:-----:|:--------:|:----|
| 1 | CB 순서 역전 | 1행 | 2~3건 | DVI 버그 수정 |
| 2 | 전환가액의조정 | 1행 | 3~5건 | DVI 버그 수정 |
| 3 | `기재정정` ADMIN 추가 | 1행 | 5~10건 | 정정공시 오분류 해결 |
| 4 | 자율공시 소괄호 | 1행 | 5건 | +10 보너스 복구 |
| 5 | 중대재해 | 3행 | 3건 | 위험 신호 복구 |
| **계** | | **7행** | **18~26건** | |

### Phase 2: 카테고리 개선 (1일)

| 순서 | 항목 | 수정량 | 영향 공시 | 효과 |
|:---:|:----|:-----:|:--------:|:----|
| 6 | OTHER→M&A 라우팅 | 3행 | 15건 | dead code 복구 |
| 7 | 매출액대비 regex | 1행 | 5~10건 | 계약점수 정상화 |
| 8 | 주식병합/비유동자산 | 2행 | 3~5건 | 카테고리 정상화 |
| 9 | 특수관계인 접두사 | 1행 | 3건 | ADMIN 정상화 |
| **계** | | **7행** | **26~33건** | |

### Phase 3: Groq 라우팅 개선 (2일, 중요)

| 순서 | 항목 | 수정량 | 영향 공시 | 효과 |
|:---:|:----|:-----:|:--------:|:----|
| 10 | _needs_llm() 함수 신규 | 30행 | 150+건 | 30~59점 재평가 |
| 11 | Groq max_tokens 최적화 | 2행 | - | 비용 상쇄 |
| **계** | | **32행** | **150+건** | **전체 분류 정확도 대폭 향상** |

### Phase 4: 수치 정규화 (3~5일)

| 순서 | 항목 | 수정량 | 영향 | 효과 |
|:---:|:----|:-----:|:---:|:----|
| 12 | 시총 조회 함수 | 15행 | 중대형 공시 | 규모 기반 점수 정밀화 |
| 13 | 스키마 변경 | DB 작업 | - | - |

---

### 최종 예상 효과 (Phase 1~3 완료 시)

| 지표 | 현재 | 개선 후 |
|:----|:---:|:-------:|
| DVI 30 무분별 fallback | ~30% (120건) | ~10% (40건) |
| 실제 dead code 로직 활용 | 10/22 패턴 | 22/22 패턴 |
| 정정공시 오분류 | 100% | 0% (ADMIN 처리) |
| Groq 분석覆盖率 | ~35% (60+점) | ~75% (30+점 + OTHERS) |
| 30~59점 구간 정확도 | 불확실 (분석 없음) | **LLM 재평가로 검증** |
| 총 규칙 수정량 | — | **46행** |

---

**핵심 원칙**:  
- 키워드가 100% 확실한 건 키워드로 처리 (0~29, 60~100)  
- 키워드가 애매한 건 (30~59, OTHER) → Groq LLM이 판단  
- Groq 비용 증가는 max_tokens 최적화와 모델 선택으로 상쇄  
