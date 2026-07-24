"use client";

import { DisclosureItem } from "@/lib/api";
import { ExternalLink, Info, Clock } from "lucide-react";

interface DisclosureCardProps {
  item: DisclosureItem;
}

// ─── Category helpers ─────────────────────────────────────────

const categoryChip: Record<string, { label: string; color: string }> = {
  ADMINISTRATIVE:    { label: "행정",       color: "border-gray-600 text-gray-400" },
  CAPITAL_RAISING:   { label: "자금조달",   color: "border-blue-600 text-blue-400" },
  BIOTECH:           { label: "바이오",     color: "border-green-600 text-green-400" },
  BUSINESS_CONTRACT: { label: "영업계약",   color: "border-purple-600 text-purple-400" },
  EARNINGS:          { label: "실적",       color: "border-yellow-600 text-yellow-400" },
  SHAREHOLDER_RETURN:{ label: "주주환원",   color: "border-teal-600 text-teal-400" },
  DELISTING_RISK:    { label: "상장위험",   color: "border-red-600 text-red-400" },
};

// ─── Signal helpers ───────────────────────────────────────────

type Signal = { icon: string; label: string; color: string; bg: string };

function getSignal(item: DisclosureItem): Signal {
  const isTrap = item.risk_flag === "HIGH_RISK_TRAP";
  const s = item.dvi_score ?? 0;

  if (item.category === "ADMINISTRATIVE")
    return { icon: "⚪", label: "행정 공시", color: "text-gray-400", bg: "bg-gray-800/40" };

  if (isTrap || s === 0)
    return { icon: "🔴", label: "위험", color: "text-red-400", bg: "bg-red-900/20" };

  if (s >= 90)
    return { icon: "🟢", label: "호재", color: "text-green-400", bg: "bg-green-900/20" };

  if (s >= 70)
    return { icon: "🟡", label: "긍정", color: "text-yellow-400", bg: "bg-yellow-900/20" };

  if (s >= 40)
    return { icon: "⚪", label: "중립", color: "text-gray-400", bg: "bg-gray-800/40" };

  return { icon: "🟠", label: "주의", color: "text-orange-400", bg: "bg-orange-900/20" };
}

// ─── Score badge ──────────────────────────────────────────────

function ScoreBadge({ score }: { score: number | null }) {
  if (score === null || score === undefined) return null;
  let barColor: string;
  let textColor: string;
  if (score >= 90)      { barColor = "bg-green-500";  textColor = "text-green-400"; }
  else if (score >= 70) { barColor = "bg-lime-500";   textColor = "text-lime-400"; }
  else if (score >= 40) { barColor = "bg-yellow-500"; textColor = "text-yellow-400"; }
  else if (score > 0)   { barColor = "bg-orange-500"; textColor = "text-orange-300"; }
  else                  { barColor = "bg-red-500";    textColor = "text-red-400"; }

  return (
    <div className="flex flex-col items-center gap-0.5">
      <div className="text-[10px] font-mono font-bold tracking-wider text-[var(--text-muted)] uppercase">DVI</div>
      <div className={`text-xl font-bold font-mono leading-none ${textColor}`}>{score}</div>
      <div className="w-full h-1 rounded-full bg-[var(--bg-primary)] overflow-hidden mt-0.5">
        <div className={`h-full rounded-full transition-all ${barColor}`} style={{ width: `${score}%` }} />
      </div>
    </div>
  );
}

// ─── Metric card ──────────────────────────────────────────────

function MetricCard({ label, value, status }: { label: string; value: string; status: string }) {
  const borderColor =
    status === "POSITIVE" ? "border-green-500/30" :
    status === "NEGATIVE" ? "border-red-500/30" :
    "border-[var(--border-color)]";
  const valueColor =
    status === "POSITIVE" ? "text-green-400" :
    status === "NEGATIVE" ? "text-red-400" :
    "text-white";

  return (
    <div className={`bg-[var(--bg-primary)] border ${borderColor} rounded-lg px-3 py-2 min-w-0`}>
      <div className="text-[10px] text-[var(--text-muted)] font-medium tracking-wider truncate">{label}</div>
      <div className={`text-sm font-semibold mt-0.5 truncate ${valueColor}`}>{value}</div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────

export default function DisclosureCard({ item }: DisclosureCardProps) {
  const cat = item.category ? categoryChip[item.category] : null;
  const signal = getSignal(item);
  const cleanTitle = item.title?.replace(/\s+/g, " ").trim() || "";
  const formattedTime = new Date(item.published_at).toLocaleString("ko-KR", {
    month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit",
  });
  const isPending = item.llm_status === "PENDING" && !item.llm_summary;
  const isTrap = item.risk_flag === "HIGH_RISK_TRAP";
  const isAdmin = item.category === "ADMINISTRATIVE";

  return (
    <div className="card p-4 animate-in hover:border-[var(--text-muted)] transition-all duration-200">
      {/* ── Row 1: Header ────────────────────────────────── */}
      <div className="flex items-start gap-3">
        {/* Left: ticker + company + category + time */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-xs font-bold text-[var(--accent-blue)] tracking-tight">
              [{item.ticker}]
            </span>
            <span className="text-sm font-semibold text-white truncate">{item.company_name}</span>
            {cat && (
              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${cat.color}`}>
                {cat.label}
              </span>
            )}
            <span className="flex items-center gap-1 text-[10px] text-[var(--text-muted)] ml-auto whitespace-nowrap">
              <Clock size={10} />
              {formattedTime}
            </span>
          </div>
          <h3 className="text-sm font-medium text-[var(--text-secondary)] mt-1 leading-snug line-clamp-2">
            {cleanTitle}
          </h3>
        </div>

        {/* Right: DVI Score */}
        <div className="shrink-0 w-16 pt-1">
          <ScoreBadge score={item.dvi_score} />
        </div>
      </div>

      {/* ── Row 2: Signal Badge ──────────────────────────── */}
      <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold mt-3 ${signal.bg} ${signal.color}`}>
        <span>{signal.icon}</span>
        <span>{signal.label}</span>
        {item.sub_type && !isAdmin && !isTrap && (
          <span className="text-[var(--text-muted)] font-normal">· {item.sub_type}</span>
        )}
      </div>

      {/* ── Row 3: AI Summary ────────────────────────────── */}
      <div className="mt-3">
        {isAdmin ? (
          <p className="text-xs text-[var(--text-muted)] italic">행정성 공시 (분석 생략)</p>
        ) : isTrap ? (
          <p className="text-xs text-red-400/70 italic">위험 공시 — FAST-FAIL 매칭 (LLM 분석 생략)</p>
        ) : isPending ? (
          <div className="space-y-1.5">
            <div className="shimmer h-3 w-full rounded" />
            <div className="shimmer h-3 w-3/4 rounded" />
          </div>
        ) : item.llm_summary ? (
          <div className="bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-lg p-3">
            <div className="flex items-center gap-1.5 mb-1.5">
              <span className="text-xs">📋</span>
              <span className="text-[10px] font-bold text-[var(--text-muted)] tracking-wider uppercase">AI 핵심 요약</span>
            </div>
            <p className="text-sm text-[var(--text-secondary)] leading-relaxed whitespace-pre-wrap">
              {item.llm_summary}
            </p>
          </div>
        ) : (
          <p className="text-xs text-[var(--text-muted)]">
            점수 {item.dvi_score} — LLM 분석 생략 (80점 이상만 요약)
          </p>
        )}
      </div>

      {/* ── Row 4: Key Metrics Grid ──────────────────────── */}
      {item.key_metrics && item.key_metrics.length > 0 && !isAdmin && (
        <div className="mt-3 grid grid-cols-2 sm:grid-cols-3 gap-2">
          {item.key_metrics.map((m, i) => (
            <MetricCard key={i} label={m.label} value={m.value} status={m.status} />
          ))}
        </div>
      )}

      {/* ── Row 5: Footer ────────────────────────────────── */}
      <div className="flex items-center justify-between mt-3 pt-2 border-t border-[var(--border-color)]">
        <a
          href={item.dart_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs text-[var(--accent-blue)] hover:text-[var(--accent-mint)] transition-colors"
        >
          <ExternalLink size={11} />
          DART 원문 보기
        </a>
        {!isAdmin && !isTrap && !isPending && item.dvi_score !== null && item.dvi_score < 80 && (
          <span className="flex items-center gap-1 text-[10px] text-[var(--text-muted)]">
            <Info size={10} />
            AI 요약 안내
          </span>
        )}
        {!isAdmin && !isTrap && !isPending && item.llm_summary && (
          <span className="flex items-center gap-1 text-[10px] text-[var(--text-muted)]">
            <Info size={10} />
            AI 분석은 참고용입니다
          </span>
        )}
      </div>
    </div>
  );
}
