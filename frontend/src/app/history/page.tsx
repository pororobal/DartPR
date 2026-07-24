"use client";

import { useState, useEffect, useCallback } from "react";
import { disclosures, DisclosureItem } from "@/lib/api";
import DisclosureCard from "@/components/DisclosureCard";
import { Search, ChevronLeft, ChevronRight, AlertCircle } from "lucide-react";

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

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      <h1 className="text-2xl font-bold text-white mb-6">히스토리</h1>

      {/* Filters */}
      <form onSubmit={handleSearch} className="card p-5 mb-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="text-xs text-[var(--text-muted)] font-bold tracking-wider">
              종목코드
            </label>
            <input
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              placeholder="예: 005930"
              className="w-full mt-1 bg-[var(--bg-hover)] border border-[var(--border-color)] rounded px-3 py-2 text-sm text-white placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-mint)]"
            />
          </div>
          <div>
            <label className="text-xs text-[var(--text-muted)] font-bold tracking-wider">
              회사명
            </label>
            <input
              type="text"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="예: 삼성전자"
              className="w-full mt-1 bg-[var(--bg-hover)] border border-[var(--border-color)] rounded px-3 py-2 text-sm text-white placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-mint)]"
            />
          </div>
          <div>
            <label className="text-xs text-[var(--text-muted)] font-bold tracking-wider">
              카테고리
            </label>
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
            <label className="text-xs text-[var(--text-muted)] font-bold tracking-wider">
              리스크
            </label>
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
            <label className="text-xs text-[var(--text-muted)] font-bold tracking-wider">
              최소 점수
            </label>
            <input
              type="number"
              min={0}
              max={100}
              value={scoreMin}
              onChange={(e) => setScoreMin(e.target.value)}
              placeholder="0"
              className="w-full mt-1 bg-[var(--bg-hover)] border border-[var(--border-color)] rounded px-3 py-2 text-sm text-white placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-mint)]"
            />
          </div>
          <div>
            <label className="text-xs text-[var(--text-muted)] font-bold tracking-wider">
              최대 점수
            </label>
            <input
              type="number"
              min={0}
              max={100}
              value={scoreMax}
              onChange={(e) => setScoreMax(e.target.value)}
              placeholder="100"
              className="w-full mt-1 bg-[var(--bg-hover)] border border-[var(--border-color)] rounded px-3 py-2 text-sm text-white placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-mint)]"
            />
          </div>
          <div>
            <label className="text-xs text-[var(--text-muted)] font-bold tracking-wider">
              시작일
            </label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="w-full mt-1 bg-[var(--bg-hover)] border border-[var(--border-color)] rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-[var(--accent-mint)]"
            />
          </div>
          <div>
            <label className="text-xs text-[var(--text-muted)] font-bold tracking-wider">
              종료일
            </label>
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
            className="btn-outline text-sm py-2 px-4"
          >
            초기화
          </button>
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
        <div className="text-center py-8">
          <AlertCircle size={32} className="text-[var(--accent-red)] mx-auto mb-2" />
          <p className="text-sm text-[var(--accent-red)]">{error}</p>
          <button onClick={fetchData} className="btn-outline mt-3 text-sm py-2 px-4">
            재시도
          </button>
        </div>
      ) : (
        <>
          <p className="text-sm text-[var(--text-secondary)] mb-3">
            총 {total}건 &middot; 페이지 {page}/{totalPages || 1}
            {total > 0 && (
              <span className="text-[var(--text-muted)] ml-2">
                (점수 범위: {Math.min(...items.filter(i => i.dvi_score !== null).map(i => i.dvi_score as number), 0)} ~ {Math.max(...items.filter(i => i.dvi_score !== null).map(i => i.dvi_score as number), 0)})
              </span>
            )}
          </p>
          <div className="space-y-3">
            {items.map((item) => (
              <DisclosureCard key={item.dart_rcept_no} item={item} />
            ))}
          </div>

          {items.length === 0 && (
            <div className="text-center py-12">
              <p className="text-[var(--text-muted)]">검색 결과가 없습니다</p>
            </div>
          )}

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-3 mt-6">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="btn-outline text-sm py-2 px-4 disabled:opacity-30"
              >
                <ChevronLeft size={16} />
              </button>
              <span className="text-sm text-[var(--text-secondary)] font-mono">
                {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="btn-outline text-sm py-2 px-4 disabled:opacity-30"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
