"use client";

import Link from "next/link";
import { Check, MessageCircle, Clock, Zap } from "lucide-react";

const plans = [
  {
    name: "Free",
    price: "무료",
    description: "비로그인으로 즉시 시작",
    features: [
      { label: "실시간 공시 피드", value: "3분 지연", included: true },
      { label: "히스토리 조회", value: "전체", included: true },
      { label: "DART 원문 링크", value: "제공", included: true },
      { label: "AI 분석 요약", value: "제공", included: true },
      { label: "트랩 의심 탐지", value: "제공", included: true },
    ],
    cta: "시작하기",
    href: "/live",
    highlighted: false,
    icon: Clock,
  },
  {
    name: "Pro",
    price: "문의",
    description: "트레이더를 위한 실시간",
    features: [
      { label: "실시간 공시 피드", value: "지연 없음", included: true },
      { label: "히스토리 조회", value: "전체", included: true },
      { label: "DART 원문 링크", value: "제공", included: true },
      { label: "AI 분석 요약", value: "제공", included: true },
      { label: "트랩 의심 탐지", value: "제공", included: true },
    ],
    cta: "카카오톡 문의",
    href: "#",
    highlighted: true,
    icon: Zap,
  },
];

export default function PricingTable() {
  return (
    <div className="grid md:grid-cols-2 gap-6 max-w-3xl mx-auto">
      {plans.map((plan) => (
        <div
          key={plan.name}
          className={`card p-6 flex flex-col ${
            plan.highlighted
              ? "border-[var(--accent-mint)] ring-1 ring-[var(--accent-mint)]"
              : ""
          }`}
        >
          {plan.highlighted && (
            <span className="text-[10px] font-bold text-[var(--accent-mint)] uppercase tracking-wider mb-2">
              추천
            </span>
          )}
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
              plan.highlighted ? "bg-[var(--accent-mint)]/10" : "bg-[var(--bg-hover)]"
            }`}>
              <plan.icon size={20} className={plan.highlighted ? "text-[var(--accent-mint)]" : "text-[var(--text-muted)]"} />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">{plan.name}</h3>
              <p className="text-xs text-[var(--text-secondary)]">{plan.description}</p>
            </div>
          </div>

          <div className="space-y-3 mt-6 flex-1">
            {plan.features.map((f, i) => (
              <div key={i} className="flex items-center gap-3">
                <Check size={14} className="text-[var(--accent-mint)] flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <span className="text-xs text-[var(--text-secondary)]">{f.label}</span>
                </div>
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                  f.value === "지연 없음"
                    ? "bg-green-900/20 text-green-400"
                    : f.value === "3분 지연"
                    ? "bg-yellow-900/20 text-yellow-400"
                    : "bg-[var(--bg-hover)] text-[var(--text-muted)]"
                }`}>
                  {f.value}
                </span>
              </div>
            ))}
          </div>

          {plan.name === "Free" ? (
            <Link href={plan.href} className="btn-primary w-full text-center mt-6 text-sm">
              {plan.cta}
            </Link>
          ) : (
            <a
              href="https://open.kakao.com/o/your-open-profile-link"
              target="_blank"
              rel="noopener noreferrer"
              className="btn-outline w-full text-center mt-6 text-sm flex items-center justify-center gap-2"
            >
              <MessageCircle size={14} />
              {plan.cta}
            </a>
          )}
        </div>
      ))}
    </div>
  );
}
