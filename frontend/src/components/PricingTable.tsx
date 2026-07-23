"use client";

import Link from "next/link";
import { Check, X, MessageCircle } from "lucide-react";

const plans = [
  {
    name: "Free",
    price: "무료",
    description: "비로그인으로 시작",
    features: [
      { label: "실시간 공시 피드", value: "전체 공개", included: true },
      { label: "히스토리 조회", value: "전체", included: true },
      { label: "DART 원문 링크", value: "제공", included: true },
      { label: "AI 분석 요약", value: "제공", included: true },
      { label: "API 자동매매 연동", value: false, included: false },
    ],
    cta: "시작하기",
    href: "/live",
    highlighted: false,
  },
  {
    name: "Pro",
    price: "문의",
    description: "트레이더용",
    features: [
      { label: "실시간 공시 피드", value: "전체 공개", included: true },
      { label: "히스토리 조회", value: "전체", included: true },
      { label: "AI 분석 요약", value: "제공", included: true },
      { label: "트랩 의심 탐지", value: "제공", included: true },
      { label: "API 자동매매 연동", value: false, included: false },
    ],
    cta: "카카오톡 문의",
    href: "#",
    highlighted: true,
  },
  {
    name: "Developer",
    price: "문의",
    description: "자동매매·개발자용",
    features: [
      { label: "실시간 공시 피드", value: "전체 공개", included: true },
      { label: "히스토리 조회", value: "전체", included: true },
      { label: "AI 분석 요약", value: "제공", included: true },
      { label: "트랩 의심 탐지", value: "제공", included: true },
      { label: "API 자동매매 연동", value: "API Key 제공", included: true },
    ],
    cta: "카카오톡 문의",
    href: "#",
    highlighted: false,
  },
];

export default function PricingTable() {
  return (
    <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
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
          <h3 className="text-lg font-bold text-white">{plan.name}</h3>
          <p className="text-2xl font-bold text-white mt-1">
            {plan.price}
            <span className="text-xs font-normal text-[var(--text-muted)] ml-1"></span>
          </p>
          <p className="text-xs text-[var(--text-secondary)] mt-1 mb-4">{plan.description}</p>

          <div className="space-y-3 flex-1">
            {plan.features.map((f, i) => (
              <div key={i} className="flex items-center gap-2">
                {f.included ? (
                  <Check size={14} className="text-[var(--accent-mint)] flex-shrink-0" />
                ) : (
                  <X size={14} className="text-[var(--text-muted)] flex-shrink-0" />
                )}
                <span className="text-xs text-[var(--text-secondary)]">
                  {f.value === true || f.value === false ? f.label : `${f.label} (${f.value})`}
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
