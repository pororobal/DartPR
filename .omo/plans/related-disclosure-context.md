# 관련공시 컨텍스트 연결 — Timeline Context Provider

## Problem

현재 모든 공시는 독립적으로 처리됨. 예: 종근당홀딩스 CKD-339 3상 IND 승인 공시 (7/27)가 5/14 IND 신청 공시와 연결되지 않아 "FDA/식약처 승인"이라는 단편적 분석만 제공.

**목표:** 공시 문서 하단 `※ 관련공시` 섹션을 파싱해 과거 공시를 자동 연결, LLM이 "5/14 신청 → 7/27 승인" 맥락을 포함한 통합 분석을 제공.

---

## Architecture Overview

```
[DART Poll] → [process_disclosure] → [Score + Insert]
                                           ↓
                                    [LLM Enrichment]
                                           ↓
                           ┌─────────────────┴─────────────────┐
                           ↓                                   ↓
                    [기본 분석 (현행)]                    [관련공시 분석 (신규)]
                    llm_summary = "승인..."             llm_summary에 MERGED
                           ↓                                   ↓
                    [Frontend 표시]                   [Frontend 업데이트]
                    "AI 핵심 요약"                     "AI 핵심 요약 (통합)"
```

## Flow (상세)

### Step 1: Insert (변경 없음)
- `_process_disclosure` → score → insert → 끝 (현행 유지)

### Step 2: Enrichment (변경)
기존 `_enrich_with_llm()`을 확장:

```
_enrich_with_llm():
  1. Groq 호출 → llm_summary 저장 (현행)
  2. _parse_related_disclosures(raw_text) → 관련공시 목록 [{date, title}]
  3. 관련공시 있으면:
     a. related_status = 'ANALYZING' UPDATE
     b. _fetch_related(rcept_no, ticker, [{date, title}])
        - Supabase에서 title LIKE 검색
        - 발견 → raw_text + llm_summary 확보
     c. _merge_analyses(current_raw, current_summary, related_raw, related_summary)
        → merged_summary 생성 (Groq 한 번 더)
     d. merged_summary + related_status = 'MERGED' UPDATE
```

### Step 3: Frontend 표시
`DisclosureCard`에 관련공시 상태 반영:

| `related_status` | 표시 |
|:----------------|:-----|
| `NONE` (or null) | 현행 유지 |
| `ANALYZING` | 현재 요약 아래 "⚡ 관련공시 분석중입니다..." (shimmer) |
| `MERGED` | 현재 요약 → `merged_summary`로 교체 + "📋 관련공시 포함 통합 분석" |

---

## 컴포넌트별 상세

### A. Backend — `backend/app/services/context_linker.py` (신규)

```python
"""
관련공시 파서 & 머저.

Dependencies: supabase, groq_service
"""

import re
from typing import Optional

_RELATED_RE = re.compile(
    r'※\s*관련공시\s+(\d{4}-\d{2}-\d{2})\s+(.+?)(?=※\s*관련공시|\Z)',
    re.DOTALL,
)


@dataclass
class RelatedDisclosure:
    date: str        # "2026-05-14"
    title: str       # "투자판단 관련 주요경영사항(...)"
    rcept_no: Optional[str] = None  # DB lookup 결과
    raw_text: Optional[str] = None
    llm_summary: Optional[str] = None


def parse_related_disclosures(raw_text: str) -> list[RelatedDisclosure]:
    """raw_text 하단 '※ 관련공시' 섹션 파싱"""
    if not raw_text:
        return []
    matches = _RELATED_RE.findall(raw_text)
    return [RelatedDisclosure(date=m[0], title=m[1].strip()) for m in matches]


async def find_in_supabase(
    related: list[RelatedDisclosure],
    ticker: str,
    supabase,
) -> list[RelatedDisclosure]:
    """Supabase에서 동일 ticker + title 유사 매칭"""
    for rd in related:
        # title의 첫 40자로 LIKE 검색 (DART 제목이 정확히 일치)
        key = rd.title[:40].strip()
        result = (
            supabase.table("disclosures")
            .select("dart_rcept_no, raw_text, llm_summary")
            .eq("ticker", ticker)
            .ilike("title", f"{key}%")
            .maybe_single()
            .execute()
        )
        if result.data:
            rd.rcept_no = result.data["dart_rcept_no"]
            rd.raw_text = result.data["raw_text"]
            rd.llm_summary = result.data["llm_summary"]
    return related


def build_merged_prompt(
    current_title: str,
    current_raw: str,
    current_summary: str,
    related_list: list[RelatedDisclosure],
) -> str:
    """현재 공시 + 관련공시 이력을 포함한 Groq prompt 생성"""
    context = f"[현재 공시]\n제목: {current_title}\n{current_raw[:3000]}\n\n"
    context += f"[현재 공시 1차 분석]\n{current_summary}\n\n"
    context += "[관련공시 이력]\n"
    for rd in sorted(related_list, key=lambda x: x.date):
        context += f"- {rd.date}: {rd.title[:80]}\n"
        if rd.llm_summary:
            context += f"  분석: {rd.llm_summary[:300]}\n"
    context += "\n위 두 공시를 종합하여 분석하라. 특히 현재 공시와 관련공시의 시간순 흐름(신청→승인, 발행→만기 등)을 설명하라."
    return context
```

### B. Backend — `backend/app/services/dart_poller.py`

기존 `_enrich_with_llm()` 확장:

```python
async def _enrich_with_llm(rcept_no, ticker, corp_name, title, raw_text, brief=False):
    # 1. 기본 분석 (현행)
    llm_result = await groq_analyze(...)
    update_data = { "llm_summary": ..., "llm_status": "DONE" }
    supabase.table("disclosures").update(update_data).eq("dart_rcept_no", rcept_no).execute()

    # 2. 관련공시 파싱
    from .context_linker import parse_related_disclosures, find_in_supabase, build_merged_prompt
    related = parse_related_disclosures(raw_text)
    if not related:
        return  # 관련공시 없음 → 종료

    # 3. ANALYZING 상태
    supabase.table("disclosures").update({
        "related_status": "ANALYZING",
    }).eq("dart_rcept_no", rcept_no).execute()

    # 4. Supabase에서 관련공시 조회
    related = await find_in_supabase(related, ticker, supabase)
    matched = [r for r in related if r.raw_text]
    if not matched:
        supabase.table("disclosures").update({
            "related_status": "NONE",
        }).eq("dart_rcept_no", rcept_no).execute()
        return

    # 5. 통합 분석
    merged_prompt = build_merged_prompt(title, raw_text, llm_result.llm_summary, matched)
    merged_result = await groq_analyze(
        ticker=ticker, company_name=corp_name,
        title=title + " (관련공시 포함)", raw_text=merged_prompt,
        brief=False,
    )

    # 6. MERGED 저장
    supabase.table("disclosures").update({
        "merged_summary": merged_result.llm_summary,
        "related_status": "MERGED",
        "related_disclosures": [
            {"date": r.date, "title": r.title, "rcept_no": r.rcept_no}
            for r in matched
        ],
    }).eq("dart_rcept_no", rcept_no).execute()
```

### C. Backend — DB Migration (Supabase SQL Editor)

```sql
ALTER TABLE disclosures 
  ADD COLUMN IF NOT EXISTS related_status TEXT DEFAULT 'NONE',
  ADD COLUMN IF NOT EXISTS merged_summary TEXT,
  ADD COLUMN IF NOT EXISTS related_disclosures JSONB DEFAULT '[]';
```

### D. Backend — Pydantic Schema (`schemas/disclosure.py`)

```python
class DisclosureResponse(BaseModel):
    # ... 기존 필드 ...
    related_status: str = "NONE"
    merged_summary: Optional[str] = None
    related_disclosures: Optional[list] = None
```

### E. Frontend — `DisclosureCard.tsx`

```tsx
// 관련공시 상태 렌더링
const relatedStatus = (item as any).related_status || "NONE";
const mergedSummary = (item as any).merged_summary;

// Row 3: AI Summary 영역에 추가
{relatedStatus === "ANALYZING" && (
  <div className="mt-2 bg-blue-900/10 border border-blue-500/20 rounded-lg p-3 animate-pulse">
    <div className="flex items-center gap-1.5 mb-1">
      <span className="text-xs">⚡</span>
      <span className="text-[10px] font-bold text-blue-400 tracking-wider uppercase">
        관련공시 분석중입니다...
      </span>
    </div>
    <div className="shimmer h-3 w-full rounded" />
    <div className="shimmer h-3 w-2/3 rounded mt-1.5" />
  </div>
)}

{relatedStatus === "MERGED" && mergedSummary && (
  <div className="mt-2 bg-[var(--bg-primary)] border border-blue-500/30 rounded-lg p-3">
    <div className="flex items-center gap-1.5 mb-1.5">
      <span className="text-xs">📋</span>
      <span className="text-[10px] font-bold text-blue-400 tracking-wider uppercase">
        관련공시 포함 통합 분석
      </span>
    </div>
    <p className="text-sm text-[var(--text-secondary)] leading-relaxed whitespace-pre-wrap">
      {mergedSummary}
    </p>
  </div>
)}
```

---

## DB Column Summary

| 컬럼 | 타입 | 설명 |
|:-----|:-----|:------|
| `related_status` | TEXT | `NONE` / `ANALYZING` / `MERGED` |
| `merged_summary` | TEXT | 통합 분석 결과 (최종) |
| `related_disclosures` | JSONB | `[{"date":"...", "title":"...", "rcept_no":"..."}]` |

## Data Flow Timeline

```
t=0:   Disclosure insert (score, category 등)
t=1s:  LLM 기본 분석 → llm_summary UPDATE
t=1s:  관련공시 발견 → related_status='ANALYZING' UPDATE
t=2s:  Frontend 첫 렌더링 (기본 분석 + "분석중입니다")
t=10s: 통합 분석 완료 → merged_summary + related_status='MERGED' UPDATE
t=11s: Frontend refetch → 통합 분석 표시
```

## 위험 & 완화

| 위험 | 완화 |
|:-----|:------|
| 관련공시가 DB에 없음 (poll 이전 공시) | `related_status='NONE'` → 조용히 종료 |
| 관련공시 파싱 실패 (포맷 예외) | fallback: 관련공시 무시, 현행 유지 |
| Groq 추가 호출 비용 | merged_summary 생성에 1회 추가 호출 (max_tokens 800) |
| ANALYZING 상태 무한 pending | 타임아웃 30초 → 실패 시 `NONE` fallback |
| raw_text에 관련공시가 많음 (3+ 건) | 가장 최근 2건만 병합 (구식은 생략) |

---

## 실행 순서

1. **DB 마이그레이션** (Supabase SQL Editor): `ALTER TABLE disclosures ADD COLUMN ...`
2. **`context_linker.py`** 신규 파일 작성
3. **`dart_poller.py`** `_enrich_with_llm()` 확장
4. **`schemas/disclosure.py`** `DisclosureResponse`에 신규 필드 추가
5. **`DisclosureCard.tsx`** 관련공시 상태 렌더링 추가
6. **변경 없음:** `api.py`, `rules_engine.py`, `groq_service.py` (기존 함수 재사용)
7. **검증:** 실제 종근당홀딩스 데이터로 end-to-end 테스트
