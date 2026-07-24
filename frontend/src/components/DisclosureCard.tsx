"use client";

import { DisclosureItem } from "@/lib/api";
import { Clock, ExternalLink, AlertTriangle, TrendingUp, TrendingDown } from "lucide-react";

interface DisclosureCardProps {
  item: DisclosureItem;
}

const categoryColors: Record<string, string> = {
  ADMINISTRATIVE: "bg-gray-700/40 text-gray-300",
  CAPITAL_RAISING: "bg-blue-900/40 text-blue-400",
  BIOTECH: "bg-green-900/40 text-green-400",
  BUSINESS_CONTRACT: "bg-purple-900/40 text-purple-400",
  EARNINGS: "bg-yellow-900/40 text-yellow-400",
  SHAREHOLDER_RETURN: "bg-teal-900/40 text-teal-400",
  DELISTING_RISK: "bg-red-900/40 text-red-400",
};

const categoryLabels: Record<string, string> = {
  ADMINISTRATIVE: "행정",
  CAPITAL_RAISING: "자금조달",
  BIOTECH: "바이오",
  BUSINESS_CONTRACT: "영업계약",
  EARNINGS: "실적",
  SHAREHOLDER_RETURN: "주주환원",
  DELISTING_RISK: "상장위험",
};

const impactColors: Record<string, string> = {
  HIGH: "bg-green-900/40 text-green-400",
  MEDIUM_HIGH: "bg-lime-900/40 text-lime-400",
  MEDIUM: "bg-yellow-900/40 text-yellow-400",
  LOW: "bg-orange-900/40 text-orange-300",
  CRITICAL: "bg-red-900/40 text-red-400",
};

function ScoreBadge({ score }: { score: number | null }) {
  if (score === null || score === undefined) return null;
  let color: string;
  if (score >= 90) color = "bg-green-600/30 text-green-400 border-green-500/40";
  else if (score >= 70) color = "bg-lime-600/30 text-lime-400 border-lime-500/40";
  else if (score >= 40) color = "bg-yellow-600/30 text-yellow-400 border-yellow-500/40";
  else if (score > 0) color = "bg-orange-600/30 text-orange-300 border-orange-500/40";
  else color = "bg-red-600/30 text-red-400 border-red-500/40";

  return (
    <span className={`text-xs font-mono font-bold px-1.5 py-0.5 rounded border ${color}`}>
      {score}
    </span>
  );
}

export default function DisclosureCard({ item }: DisclosureCardProps) {
  const catColor = item.category
    ? categoryColors[item.category] || "bg-gray-800 text-gray-400"
    : "bg-gray-800 text-gray-400";
  const catLabel = item.category
    ? categoryLabels[item.category] || item.category
    : "기타";

  const formattedTime = new Date(item.published_at).toLocaleString("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });

  const isPending = item.llm_status === "PENDING" && !item.llm_summary;
  const isTrap = item.risk_flag === "HIGH_RISK_TRAP";
  const isAdmin = item.category === "ADMINISTRATIVE";
  const cleanTitle = item.title?.replace(/\s+/g, " ").trim() || "";

  return (
    <div className="card p-5 animate-in hover:border-[var(--text-muted)] transition-all duration-200">
      {/* Top row: ticker + category + score + time */}
      <div className="flex items-center gap-2 flex-wrap mb-2">
        <span className="font-mono text-sm font-bold text-[var(--accent-blue)] tracking-tight">
          {item.ticker}
        </span>
        {item.category && (
          <span className={`category-tag ${catColor}`}>{catLabel}</span>
        )}
        {item.sub_type && !isAdmin && (
          <span className="text-xs text-[var(--text-muted)]">{item.sub_type}</span>
        )}
        <ScoreBadge score={item.dvi_score} />
        {isTrap && (
          <span className="category-tag bg-red-900/40 text-red-400 flex items-center gap-1">
            <AlertTriangle size={11} />
            위험
          </span>
        )}
        {item.impact_level === "CRITICAL" && !isTrap && (
          <span className="category-tag bg-red-800/30 text-red-300 text-[10px]">
            CRITICAL
          </span>
        )}
        <span className="flex items-center gap-1 text-xs text-[var(--text-muted)] ml-auto whitespace-nowrap">
          <Clock size={12} />
          {formattedTime}
        </span>
      </div>

      {/* Company name + Title */}
      <div className="mb-1">
        <h3 className="text-base font-bold text-white leading-snug">
          {item.company_name}
        </h3>
        <p className="text-sm text-[var(--text-secondary)] mt-0.5 leading-snug line-clamp-2">
          {cleanTitle}
        </p>
      </div>

      {/* DART original link */}
      {item.dart_url && (
        <div className="mb-2">
          <a
            href={item.dart_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-[var(--accent-blue)] hover:text-[var(--accent-mint)] transition-colors"
          >
            <ExternalLink size={12} />
            DART 원문 보기
          </a>
        </div>
      )}

      {/* LLM Summary — only for non-admin, non-trap, score >= 80 */}
      {isAdmin ? (
        <div className="pt-1">
          <p className="text-xs text-[var(--text-muted)] italic">
            행정성 공시 (채점·분석 생략)
          </p>
        </div>
      ) : isTrap ? (
        <div className="pt-1">
          <p className="text-xs text-red-400/70 italic">
            위험 공시 — FAST-FAIL 매칭 (LLM 분석 생략)
          </p>
        </div>
      ) : isPending ? (
        <div className="space-y-1.5 pt-1">
          <div className="shimmer h-3.5 w-full" />
          <div className="shimmer h-3.5 w-3/4" />
        </div>
      ) : item.llm_summary ? (
        <div className="pt-1">
          <p className="text-sm text-[var(--text-secondary)] leading-relaxed border-l-2 border-[var(--accent-mint)] pl-3">
            {item.llm_summary}
          </p>
        </div>
      ) : item.dvi_score !== null && item.dvi_score < 80 && (
        <div className="pt-1">
          <p className="text-xs text-[var(--text-muted)]">
            점수 {item.dvi_score} — LLM 분석 생략
          </p>
        </div>
      )}

      {/* Momentum / risk indicator */}
      {item.momentum_authenticity && !isAdmin && !isTrap && (
        <div className="flex items-center gap-1 mt-2">
          {item.momentum_authenticity === "HIGH" ? (
            <TrendingUp size={12} className="text-green-400" />
          ) : item.momentum_authenticity === "LOW" ? (
            <TrendingDown size={12} className="text-red-400" />
          ) : null}
          {item.momentum_authenticity && (
            <span className="text-[10px] text-[var(--text-muted)] uppercase">
              {item.momentum_authenticity}
            </span>
          )}
        </div>
      )}

      {/* Key metrics */}
      {item.key_metrics && item.key_metrics.length > 0 && (
        <div className="flex gap-2 flex-wrap pt-2">
          {item.key_metrics.map((m, i) => (
            <span
              key={i}
              className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                m.status === "POSITIVE"
                  ? "bg-green-900/20 text-green-400"
                  : m.status === "NEGATIVE"
                  ? "bg-red-900/20 text-red-400"
                  : "bg-gray-800 text-gray-400"
              }`}
            >
              {m.label}: {m.value}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
