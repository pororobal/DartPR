"use client";

import { DisclosureItem } from "@/lib/api";
import ScoreBadge from "./ScoreBadge";
import { Clock, AlertTriangle } from "lucide-react";

interface DisclosureCardProps {
  item: DisclosureItem;
}

const categoryColors: Record<string, string> = {
  CAPITAL_RAISING: "bg-blue-900/40 text-blue-400",
  BIOTECH: "bg-green-900/40 text-green-400",
  BUSINESS_CONTRACT: "bg-purple-900/40 text-purple-400",
  EARNINGS: "bg-yellow-900/40 text-yellow-400",
  SHAREHOLDER_RETURN: "bg-teal-900/40 text-teal-400",
  DELISTING_RISK: "bg-red-900/40 text-red-400",
};

const categoryLabels: Record<string, string> = {
  CAPITAL_RAISING: "자금조달",
  BIOTECH: "바이오",
  BUSINESS_CONTRACT: "영업계약",
  EARNINGS: "실적",
  SHAREHOLDER_RETURN: "주주환원",
  DELISTING_RISK: "상장위험",
};

export default function DisclosureCard({ item }: DisclosureCardProps) {
  const catColor = item.category ? categoryColors[item.category] || "bg-gray-800 text-gray-400" : "bg-gray-800 text-gray-400";
  const catLabel = item.category ? categoryLabels[item.category] || item.category : "기타";

  const formattedTime = new Date(item.published_at).toLocaleString("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });

  const isPending = item.llm_status === "PENDING";
  const isHighRisk = item.risk_flag === "HIGH_RISK_TRAP";

  return (
    <div className="card p-4 animate-in">
      <div className="flex items-start justify-between gap-3">
        {/* Left: content */}
        <div className="flex-1 min-w-0">
          {/* Top row: ticker + category + time */}
          <div className="flex items-center gap-2 flex-wrap mb-1.5">
            <span className="font-mono text-xs font-bold text-[var(--accent-blue)]">
              {item.ticker}
            </span>
            {item.category && (
              <span className={`category-tag ${catColor}`}>{catLabel}</span>
            )}
            {isHighRisk && (
              <span className="category-tag bg-red-900/40 text-red-400 flex items-center gap-1">
                <AlertTriangle size={10} />
                리스크
              </span>
            )}
            <span className="flex items-center gap-1 text-[10px] text-[var(--text-muted)] ml-auto">
              <Clock size={10} />
              {formattedTime}
            </span>
          </div>

          {/* Company name */}
          <h3 className="text-sm font-semibold text-white truncate">
            {item.company_name}
          </h3>

          {/* Title */}
          <p className="text-xs text-[var(--text-secondary)] mt-0.5 line-clamp-2">
            {item.title}
          </p>

          {/* LLM Summary — 2-stage loading */}
          {isPending ? (
            <div className="mt-2 space-y-1.5">
              <div className="shimmer h-3 w-full" />
              <div className="shimmer h-3 w-3/4" />
            </div>
          ) : item.llm_summary ? (
            <p className="text-xs text-[var(--text-secondary)] mt-2 italic border-l-2 border-[var(--accent-mint)] pl-2">
              {item.llm_summary}
            </p>
          ) : null}

          {/* Key metrics */}
          {item.key_metrics && item.key_metrics.length > 0 && (
            <div className="flex gap-3 mt-2 flex-wrap">
              {item.key_metrics.map((m, i) => (
                <span
                  key={i}
                  className={`text-[10px] px-2 py-0.5 rounded-full ${
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

        {/* Right: score badge */}
        <div className="flex-shrink-0">
          <ScoreBadge score={item.dvi_score} size="lg" />
        </div>
      </div>
    </div>
  );
}
