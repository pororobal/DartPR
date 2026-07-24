"use client";

import { useState, useEffect, useCallback } from "react";
import { disclosures, DisclosureItem } from "@/lib/api";
import DisclosureCard from "@/components/DisclosureCard";
import {
  Search, ChevronLeft, ChevronRight, AlertCircle,
  ChevronDown, ChevronUp, SlidersHorizontal, X, Calendar,
  TrendingUp, Shield, RotateCcw
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

const quickFilters: { label: string; icon: any; apply: () => QuickFilterVals }[] = [
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

  // Filters
  const [ticker, setTicker] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [category, setCategory] = useState("");
  const [scoreMin, setScoreMin] = useState("");
  const [scoreMax, setScoreMax] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [riskFlag, setRiskFlag] = useState("");

  const [filterOpen, setFilterOpen] = useState(false);

  const hasActiveFilters = ticker || companyName || category || scoreMin || scoreMax || dateFrom || dateTo || riskFlag;

  const buildParams = useCallback(() => {
    const params: Record<string, string | number> = { page, per_page: perPage };
    if (ticker) params.ticker = ticker;
    if (companyName) params.company_name = companyName;
    if (category) params.category = category;
    if (scoreMin) params.score_min = Number(scoreMin);
    if (scoreMax) params.score_max = Number(scoreMax);
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    if (riskFlag) params.risk_flag = riskFlag;
    return params;
  }, [page, ticker, companyName, category, scoreMin, scoreMax, dateFrom, dateTo, riskFlag]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await disclosures.history(buildParams() as any);
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

  const totalPages = Math.ceil(total / perPage);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchData();
  };

  const handleReset = () => {
    setTicker("");
    setCompanyName("");
    setCategory("");
    setScoreMin("");
    setScoreMax("");
    setDateFrom("");
    setDateTo("");
    setRiskFlag("");
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

      {/* Collapsible filter panel */}
      <form onSubmit={handleSearch}>
        <div className="card mb-6">
          <button
            type="button"
            onClick={() => setFilterOpen(!filterOpen)}
            className="w-full flex items-center justify-between p-4 text-sm"
          >
            <div className="flex items-center gap-2">
              <SlidersHorizontal size={14} className="text-[var(--accent-mint)]" />
              <span className="text-white font-medium">필터</span>
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
                  <label className="text-xs text-[var(--text-muted)] font-bold tracking-wider">종목코드</label>
                  <input
                    type="text"
                    value={ticker}
                    onChange={(e) => setTicker(e.target.value)}
                    placeholder="예: 005930"
                    className="w-full mt-1 bg-[var(--bg-hover)] border border-[var(--border-color)] rounded px-3 py-2 text-sm text-white placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-mint)]"
                  />
                </div>
                <div>
                  <label className="text-xs text-[var(--text-muted)] font-bold tracking-wider">회사명</label>
                  <input
                    type="text"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    placeholder="예: 삼성전자"
                    className="w-full mt-1 bg-[var(--bg-hover)] border border-[var(--border-color)] rounded px-3 py-2 text-sm text-white placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-mint)]"
                  />
                </div>
                <div>
                  <label className="text-xs text-[var(--text-muted)] font-bold tracking-wider">카테고리</label>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
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
                    value={riskFlag}
                    onChange={(e) => setRiskFlag(e.target.value)}
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
                    value={scoreMin}
                    onChange={(e) => setScoreMin(e.target.value)}
                    placeholder="0"
                    className="w-full mt-1 bg-[var(--bg-hover)] border border-[var(--border-color)] rounded px-3 py-2 text-sm text-white placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-mint)]"
                  />
                </div>
                <div>
                  <label className="text-xs text-[var(--text-muted)] font-bold tracking-wider">최대 점수</label>
                  <input
                    type="number" min={0} max={100}
                    value={scoreMax}
                    onChange={(e) => setScoreMax(e.target.value)}
                    placeholder="100"
                    className="w-full mt-1 bg-[var(--bg-hover)] border border-[var(--border-color)] rounded px-3 py-2 text-sm text-white placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-mint)]"
                  />
                </div>
                <div>
                  <label className="text-xs text-[var(--text-muted)] font-bold tracking-wider">시작일</label>
                  <input
                    type="date"
                    value={dateFrom}
                    onChange={(e) => setDateFrom(e.target.value)}
                    className="w-full mt-1 bg-[var(--bg-hover)] border border-[var(--border-color)] rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-[var(--accent-mint)]"
                  />
                </div>
                <div>
                  <label className="text-xs text-[var(--text-muted)] font-bold tracking-wider">종료일</label>
                  <input
                    type="date"
                    value={dateTo}
                    onChange={(e) => setDateTo(e.target.value)}
                    className="w-full mt-1 bg-[var(--bg-hover)] border border-[var(--border-color)] rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-[var(--accent-mint)]"
                  />
                </div>
              </div>
              <div className="flex gap-2 mt-4">
                <button
                  type="submit"
                  className="btn-primary text-sm py-2 px-5 flex items-center gap-1.5"
                >
                  <Search size={14} />
                  검색
                </button>
                <button
                  type="button"
                  onClick={handleReset}
                  className="btn-outline text-sm py-2 px-4 flex items-center gap-1.5"
                >
                  <X size={14} />
                  초기화
                </button>
              </div>
            </div>
          )}
        </div>
      </form>

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
              <DisclosureCard key={item.dart_rcept_no} item={item} />
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
            </div>
          )}
        </>
      )}
    </div>
  );
}
