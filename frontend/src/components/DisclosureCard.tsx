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

  // Clean up title — strip leading brackets noise and extra whitespace
  const cleanTitle = item.title?.replace(/\s+/g, " ").trim() || "";

  return (
    <div className="card p-5 animate-in hover:border-[var(--text-muted)] transition-all duration-200">
      <div className="flex items-start justify-between gap-4">
        {/* Left: content */}
        <div className="flex-1 min-w-0 space-y-2">
          {/* Top row: ticker + category + time */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-sm font-bold text-[var(--accent-blue)] tracking-tight">
              {item.ticker}
            </span>
            {item.category && (
              <span className={`category-tag ${catColor}`}>{catLabel}</span>
            )}
            {isHighRisk && (
              <span className="category-tag bg-red-900/40 text-red-400 flex items-center gap-1">
                <AlertTriangle size={11} />
                리스크
              </span>
            )}
            <span className="flex items-center gap-1 text-xs text-[var(--text-muted)] ml-auto whitespace-nowrap">
              <Clock size={12} />
              {formattedTime}
            </span>
          </div>

          {/* Company name + Title */}
          <div>
            <h3 className="text-base font-bold text-white leading-snug">
              {item.company_name}
            </h3>
            <p className="text-sm text-[var(--text-secondary)] mt-0.5 leading-snug line-clamp-2">
              {cleanTitle}
            </p>
          </div>

          {/* LLM Summary — 2-stage loading */}
          {isPending ? (
            <div className="space-y-1.5 pt-1">
              <div className="shimmer h-3.5 w-full" />
              <div className="shimmer h-3.5 w-3/4" />
            </div>
          ) : item.llm_summary ? (
            <div className="pt-1">
              <p className="text-sm text-[var(--text-secondary)] leading-relaxed italic border-l-2 border-[var(--accent-mint)] pl-3">
                {item.llm_summary}
              </p>
            </div>
          ) : null}

          {/* Key metrics */}
          {item.key_metrics && item.key_metrics.length > 0 && (
            <div className="flex gap-2 flex-wrap pt-0.5">
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

        {/* Right: score badge */}
        <div className="flex-shrink-0 pt-1">
          <ScoreBadge score={item.dvi_score} size="lg" />
        </div>
      </div>
    </div>
  );
}
