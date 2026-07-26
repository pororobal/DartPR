"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { disclosures, DisclosureItem, auth, type CompanySuggestion } from "@/lib/api";
import DisclosureCard from "@/components/DisclosureCard";
import {
  Search, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, AlertCircle,
  ChevronDown, ChevronUp, SlidersHorizontal, X, Calendar,
  TrendingUp, Shield, RotateCcw, type LucideIcon
} from "lucide-react";

const categories = [
  { value: "", label: "전체" },
  { value: "ADMINISTRATIVE", label: "행정" },
  { value: "CAPITAL_RAISING", label: "자금조달" },
  { value: "BIOTECH", label: "바이오" },
  { value: "BUSINESS_CONTRACT", label: "영업계약" },
  { value: "EARNINGS", label: "실적" },
  { value: "SHAREHOLDER_RETURN", label: "주주환원" },
  { value: "DELISTING_RISK", label: "상장위험" },
];

const riskFlags = [
  { value: "", label: "전체" },
  { value: "HIGH_RISK_TRAP", label: "위험 공시" },
];

function getToday() {
  return new Date().toISOString().slice(0, 10);
}

function getWeekStart() {
  const d = new Date();
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1);
  d.setDate(diff);
  return d.toISOString().slice(0, 10);
}

interface QuickFilterVals {
  dateFrom?: string;
  dateTo?: string;
  scoreMin?: string;
  scoreMax?: string;
  riskFlag?: string;
}

const quickFilters: { label: string; icon: LucideIcon; apply: () => QuickFilterVals }[] = [
  { label: "오늘", icon: Calendar, apply: () => ({ dateFrom: getToday(), dateTo: getToday() }) },
  { label: "이번주", icon: Calendar, apply: () => ({ dateFrom: getWeekStart(), dateTo: getToday() }) },
  { label: "고득점 (80+)", icon: TrendingUp, apply: () => ({ scoreMin: "80", scoreMax: "" }) },
  { label: "위험 공시", icon: Shield, apply: () => ({ riskFlag: "HIGH_RISK_TRAP" }) },
];

export default function HistoryPage() {
  const [items, setItems] = useState<DisclosureItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const perPage = 20;
  const [isAdmin, setIsAdmin] = useState(false);

  // Check if user is admin
  useEffect(() => {
    const checkAdmin = async () => {
      try {
        const userData = await auth.me();
        setIsAdmin(userData.plan === "admin");
      } catch {
        setIsAdmin(false);
      }
    };
    checkAdmin();
  }, []);

  // Filters — searchInput is the live input, searchQuery is the applied value
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [category, setCategory] = useState("");
  const [scoreMin, setScoreMin] = useState("");
  const [scoreMax, setScoreMax] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [riskFlag, setRiskFlag] = useState("");

  const [filterOpen, setFilterOpen] = useState(false);

  // Draft filter states (batch-apply via "적용" button)
  const [draftCategory, setDraftCategory] = useState("");
  const [draftScoreMin, setDraftScoreMin] = useState("");
  const [draftScoreMax, setDraftScoreMax] = useState("");
  const [draftDateFrom, setDraftDateFrom] = useState("");
  const [draftDateTo, setDraftDateTo] = useState("");
  const [draftRiskFlag, setDraftRiskFlag] = useState("");

  // Sync drafts when opening filter panel
  const openFilterPanel = () => {
    setDraftCategory(category);
    setDraftScoreMin(scoreMin);
    setDraftScoreMax(scoreMax);
    setDraftDateFrom(dateFrom);
    setDraftDateTo(dateTo);
    setDraftRiskFlag(riskFlag);
    setFilterOpen(true);
  };

  const applyFilters = () => {
    setCategory(draftCategory);
    setScoreMin(draftScoreMin);
    setScoreMax(draftScoreMax);
    setDateFrom(draftDateFrom);
    setDateTo(draftDateTo);
    setRiskFlag(draftRiskFlag);
    setFilterOpen(false);
    setPage(1);
  };

  const cancelFilters = () => {
    setFilterOpen(false);
  };

  // Autocomplete state
  const [suggestions, setSuggestions] = useState<CompanySuggestion[]>([]);
  const [suggestLoading, setSuggestLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestActiveIdx, setSuggestActiveIdx] = useState(-1);
  const suggestRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const isComposingRef = useRef(false);

  const hasActiveFilters = searchQuery || category || scoreMin !== "" || scoreMax !== "" || dateFrom || dateTo || riskFlag;
  const isSearchDirty = searchInput !== searchQuery;

  const buildParams = useCallback(() => {
    const params: Record<string, string | number> = { page, per_page: perPage };
    if (searchQuery) params.q = searchQuery; // searchQuery, not searchInput — only applied on submit
    if (category) params.category = category;
    if (scoreMin !== "") params.score_min = Number(scoreMin);
    if (scoreMax !== "") params.score_max = Number(scoreMax);
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    if (riskFlag) params.risk_flag = riskFlag;
    return params;
  }, [page, searchQuery, category, scoreMin, scoreMax, dateFrom, dateTo, riskFlag]);

  type HistoryParams = Parameters<typeof disclosures.history>[0];

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await disclosures.history(buildParams() as HistoryParams);
      setItems(result.data || []);
      setTotal(result.total || 0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch");
    } finally {
      setLoading(false);
    }
  }, [buildParams]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Debounced autocomplete fetch (respects IME composition)
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!searchInput.trim() || searchInput.length < 1) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }
    if (isComposingRef.current) return;
    setSuggestLoading(true);
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await disclosures.suggest(searchInput.trim());
        setSuggestions(res.suggestions);
        setShowSuggestions(true);
        setSuggestActiveIdx(-1);
      } catch {
        setSuggestions([]);
        setShowSuggestions(true);
      } finally {
        setSuggestLoading(false);
      }
    }, 200);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [searchInput]);

  // Click outside to close suggestions
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (suggestRef.current && !suggestRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const totalPages = Math.ceil(total / perPage);

  const handleSelectSuggestion = (s: CompanySuggestion) => {
    setSearchInput(s.company_name);
    setSearchQuery(s.company_name);
    setShowSuggestions(false);
    setPage(1);
  };

  const handleSuggestKeyDown = (e: React.KeyboardEvent) => {
    if (!showSuggestions || suggestions.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSuggestActiveIdx((prev) => (prev < suggestions.length - 1 ? prev + 1 : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSuggestActiveIdx((prev) => (prev > 0 ? prev - 1 : suggestions.length - 1));
    } else if (e.key === "Enter" && suggestActiveIdx >= 0) {
      e.preventDefault();
      handleSelectSuggestion(suggestions[suggestActiveIdx]);
    } else if (e.key === "Escape") {
      setShowSuggestions(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchQuery(searchInput); // apply the typed value
    setShowSuggestions(false);
    setPage(1);
  };

  const handleReset = () => {
    setSearchInput("");
    setSearchQuery("");
    setCategory("");
    setScoreMin("");
    setScoreMax("");
    setDateFrom("");
    setDateTo("");
    setRiskFlag("");
    setFilterOpen(false);
    setPage(1);
  };

  const applyQuickFilter = (qf: typeof quickFilters[0]) => {
    const vals = qf.apply();
    if (vals.dateFrom !== undefined) setDateFrom(vals.dateFrom);
    if (vals.dateTo !== undefined) setDateTo(vals.dateTo);
    if (vals.scoreMin !== undefined) setScoreMin(vals.scoreMin);
    if (vals.scoreMax !== undefined) setScoreMax(vals.scoreMax || "");
    if (vals.riskFlag !== undefined) setRiskFlag(vals.riskFlag);
    setPage(1);
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">히스토리 조회</h1>
        <p className="text-xs text-[var(--text-secondary)] mt-1">
          지난 공시를 검색하고 분석 결과를 확인하세요
        </p>
      </div>

      {/* Unified search bar — always visible */}
      <form onSubmit={handleSearch} className="mb-4">
        <div className="flex items-center gap-2">
          <div ref={suggestRef} className="relative flex-1">
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={handleSuggestKeyDown}
              onFocus={() => { if (suggestions.length > 0) setShowSuggestions(true); }}
              onCompositionStart={() => { isComposingRef.current = true; }}
              onCompositionEnd={() => { isComposingRef.current = false; }}
              placeholder="종목코드 또는 회사명 입력 (예: 005930, 삼성전자)"
              className="w-full bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg pl-4 pr-9 py-2.5 text-sm text-white placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-mint)]"
            />
            {/* 검색어 X 버튼 */}
            {searchInput && (
              <button
                type="button"
                onClick={() => { setSearchInput(""); setShowSuggestions(false); }}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-white transition-colors p-1"
              >
                <X size={14} />
              </button>
            )}
            {/* Autocomplete dropdown */}
            {showSuggestions && (
              <div className="absolute z-50 top-full left-0 right-0 mt-1 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg shadow-lg overflow-hidden max-h-60 overflow-y-auto">
                {suggestLoading && (
                  <div className="px-3 py-2 text-xs text-[var(--text-muted)]">검색 중...</div>
                )}
                {!suggestLoading && suggestions.length > 0 && suggestions.map((s, i) => (
                  <button
                    key={`${s.ticker}-${s.company_name}`}
                    type="button"
                    onMouseDown={(e) => { e.preventDefault(); handleSelectSuggestion(s); }}
                    className={`w-full text-left px-3 py-2 text-sm flex items-center justify-between gap-2 transition-colors ${
                      i === suggestActiveIdx
                        ? "bg-[var(--accent-mint)]/10 text-[var(--accent-mint)]"
                        : "text-white hover:bg-[var(--bg-hover)]"
                    }`}
                  >
                    <span className="truncate">{s.company_name}</span>
                    <span className="shrink-0 text-[10px] font-mono text-[var(--text-muted)]">{s.ticker}</span>
                  </button>
                ))}
                {!suggestLoading && suggestions.length === 0 && (
                  <div className="px-3 py-3 text-xs text-[var(--text-muted)] text-center">
                    검색 결과가 없습니다
                  </div>
                )}
              </div>
            )}
          </div>
          <button type="submit" className="btn-primary text-sm py-2.5 px-5 flex items-center gap-1.5 shrink-0">
            <Search size={14} />
            검색
          </button>
        </div>
      </form>

      {/* Quick filter chips */}
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        {quickFilters.map((qf) => (
          <button
            key={qf.label}
            onClick={() => applyQuickFilter(qf)}
            className="flex items-center gap-1.5 text-[11px] text-[var(--text-secondary)] bg-[var(--bg-card)] border border-[var(--border-color)] px-3 py-1.5 rounded-full hover:text-white hover:border-[var(--accent-mint)]/40 transition-colors"
          >
            <qf.icon size={12} />
            {qf.label}
          </button>
        ))}

        {hasActiveFilters && (
          <button
            onClick={handleReset}
            className="flex items-center gap-1.5 text-[11px] text-red-400 bg-red-900/10 border border-red-900/30 px-3 py-1.5 rounded-full hover:text-red-300 transition-colors"
          >
            <RotateCcw size={12} />
            초기화
          </button>
        )}
      </div>

      {/* Collapsible advanced filters */}
      <div className="card mb-6">
        <button
          type="button"
          onClick={() => filterOpen ? cancelFilters() : openFilterPanel()}
          className="w-full flex items-center justify-between p-4 text-sm"
        >
          <div className="flex items-center gap-2">
            <SlidersHorizontal size={14} className="text-[var(--accent-mint)]" />
            <span className="text-white font-medium">상세 필터</span>
            {hasActiveFilters && (
              <span className="text-[10px] bg-[var(--accent-mint)]/10 text-[var(--accent-mint)] px-2 py-0.5 rounded-full">
                활성화됨
              </span>
            )}
          </div>
          {filterOpen ? (
            <ChevronUp size={16} className="text-[var(--text-muted)]" />
          ) : (
            <ChevronDown size={16} className="text-[var(--text-muted)]" />
          )}
        </button>

        {filterOpen && (
          <div className="px-4 pb-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <label className="text-xs text-[var(--text-muted)] font-bold tracking-wider">카테고리</label>
                <select
                  value={draftCategory}
                  onChange={(e) => setDraftCategory(e.target.value)}
                  className="w-full mt-1 bg-[var(--bg-hover)] border border-[var(--border-color)] rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-[var(--accent-mint)]"
                >
                  {categories.map((c) => (
                    <option key={c.value} value={c.value}>{c.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-[var(--text-muted)] font-bold tracking-wider">리스크</label>
                <select
                  value={draftRiskFlag}
                  onChange={(e) => setDraftRiskFlag(e.target.value)}
                  className="w-full mt-1 bg-[var(--bg-hover)] border border-[var(--border-color)] rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-[var(--accent-mint)]"
                >
                  {riskFlags.map((r) => (
                    <option key={r.value} value={r.value}>{r.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-[var(--text-muted)] font-bold tracking-wider">최소 점수</label>
                <input
                  type="number" min={0} max={100}
                  value={draftScoreMin}
                  onChange={(e) => setDraftScoreMin(e.target.value)}
                  placeholder="0"
                  className="w-full mt-1 bg-[var(--bg-hover)] border border-[var(--border-color)] rounded px-3 py-2 text-sm text-white placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-mint)]"
                />
              </div>
              <div>
                <label className="text-xs text-[var(--text-muted)] font-bold tracking-wider">최대 점수</label>
                <input
                  type="number" min={0} max={100}
                  value={draftScoreMax}
                  onChange={(e) => setDraftScoreMax(e.target.value)}
                  placeholder="100"
                  className="w-full mt-1 bg-[var(--bg-hover)] border border-[var(--border-color)] rounded px-3 py-2 text-sm text-white placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-mint)]"
                />
              </div>
              <div>
                <label className="text-xs text-[var(--text-muted)] font-bold tracking-wider">시작일</label>
                <input
                  type="date"
                  value={draftDateFrom}
                  onChange={(e) => setDraftDateFrom(e.target.value)}
                  className="w-full mt-1 bg-[var(--bg-hover)] border border-[var(--border-color)] rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-[var(--accent-mint)]"
                />
              </div>
              <div>
                <label className="text-xs text-[var(--text-muted)] font-bold tracking-wider">종료일</label>
                <input
                  type="date"
                  value={draftDateTo}
                  onChange={(e) => setDraftDateTo(e.target.value)}
                  className="w-full mt-1 bg-[var(--bg-hover)] border border-[var(--border-color)] rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-[var(--accent-mint)]"
                />
              </div>
            </div>
            {/* 적용/취소 버튼 */}
            <div className="flex items-center justify-end gap-2 mt-4 pt-3 border-t border-[var(--border-color)]">
              <button onClick={cancelFilters} className="btn-outline text-xs py-2 px-4">
                취소
              </button>
              <button onClick={applyFilters} className="btn-primary text-xs py-2 px-4">
                <SlidersHorizontal size={12} />
                적용
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Results */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="card p-5">
              <div className="shimmer h-4 w-24 mb-2" />
              <div className="shimmer h-5 w-3/4 mb-1" />
              <div className="shimmer h-4 w-full" />
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="card p-8 text-center">
          <AlertCircle size={32} className="text-red-400 mx-auto mb-2" />
          <p className="text-sm text-red-400">{error}</p>
          <button onClick={fetchData} className="btn-outline mt-3 text-sm py-2 px-4">
            재시도
          </button>
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm text-[var(--text-secondary)]">
              총 <span className="text-white font-bold">{total}</span>건 검색됨
            </p>
            <p className="text-xs text-[var(--text-muted)] font-mono">
              {page} / {totalPages || 1}
            </p>
          </div>

          {items.length > 0 && (
            <div className="w-full h-1.5 rounded-full bg-[var(--bg-card)] mb-4 overflow-hidden flex">
              {(() => {
                const scores = items.filter(i => i.dvi_score != null).map(i => i.dvi_score as number);
                const high = scores.filter(s => s >= 70).length;
                const mid = scores.filter(s => s >= 40 && s < 70).length;
                const low = scores.filter(s => s < 40).length;
                const total2 = high + mid + low || 1;
                return (
                  <>
                    <div
                      className="h-full bg-green-500/50 transition-all"
                      style={{ width: `${(high / total2) * 100}%` }}
                      title={`고득점(70+): ${high}건`}
                    />
                    <div
                      className="h-full bg-yellow-500/40 transition-all"
                      style={{ width: `${(mid / total2) * 100}%` }}
                      title={`중간(40-69): ${mid}건`}
                    />
                    <div
                      className="h-full bg-red-500/40 transition-all"
                      style={{ width: `${(low / total2) * 100}%` }}
                      title={`저득점(-40): ${low}건`}
                    />
                  </>
                );
              })()}
            </div>
          )}

          <div className="space-y-3">
            {items.map((item) => (
              <DisclosureCard key={item.dart_rcept_no} item={item} isAdmin={isAdmin} />
            ))}
          </div>

          {items.length === 0 && (
            <div className="card p-12 text-center">
              <Search size={32} className="mx-auto text-[var(--text-muted)] mb-3" />
              <p className="text-[var(--text-secondary)] text-sm">검색 결과가 없습니다</p>
              <p className="text-xs text-[var(--text-muted)] mt-1">
                필터를 변경하고 다시 검색해보세요
              </p>
            </div>
          )}

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-8">
              <button
                onClick={() => setPage(1)}
                disabled={page <= 1}
                className="btn-outline text-xs flex items-center gap-1 disabled:opacity-30"
              >
                <ChevronsLeft size={14} />
              </button>
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="btn-outline text-xs flex items-center gap-1 disabled:opacity-30"
              >
                <ChevronLeft size={14} /> 이전
              </button>

              {Array.from({ length: Math.min(totalPages, 5) }).map((_, i) => {
                const start = Math.max(1, Math.min(page - 2, totalPages - 4));
                const p = start + i;
                if (p > totalPages) return null;
                return (
                  <button
                    key={p}
                    onClick={() => setPage(p)}
                    className={`w-8 h-8 rounded-lg text-xs font-medium transition-colors ${
                      p === page
                        ? "bg-[var(--accent-mint)] text-black"
                        : "text-[var(--text-secondary)] hover:text-white"
                    }`}
                  >
                    {p}
                  </button>
                );
              })}

              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="btn-outline text-xs flex items-center gap-1 disabled:opacity-30"
              >
                다음 <ChevronRight size={14} />
              </button>
              <button
                onClick={() => setPage(totalPages)}
                disabled={page >= totalPages}
                className="btn-outline text-xs flex items-center gap-1 disabled:opacity-30"
              >
                <ChevronsRight size={14} />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
