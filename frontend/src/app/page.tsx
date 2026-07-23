"use client";

import Link from "next/link";
import { BarChart3, Brain, History, ArrowRight } from "lucide-react";
import PricingTable from "@/components/PricingTable";

const features = [
  {
    icon: <BarChart3 size={24} />,
    title: "실시간 DART 공시 — 카테고리로 바로 분류",
    desc: "자금조달·바이오·실적·주주환원 등 카테고리별로 실시간 분류. 원하는 공시만 골라 보세요.",
  },
  {
    icon: <Brain size={24} />,
    title: "AI가 원문을 분석해 요약해드립니다",
    desc: "숫자 뒤에 숨은 맥락 — 진짜 호재인지, 트랩인지 — 를 AI가 문장으로 풀어드립니다.",
  },
  {
    icon: <History size={24} />,
    title: "히스토리 조회로 지난 공시도 한눈에",
    desc: "카테고리와 종목코드로 원하는 공시를 검색하고 AI 분석 결과까지 함께 확인하세요.",
  },
];

export default function LandingPage() {
  return (
    <div>
      <section className="relative min-h-[80vh] flex items-center justify-center px-4">
        <div className="absolute inset-0 bg-gradient-to-b from-[var(--accent-mint)]/5 to-transparent pointer-events-none" />
        <div className="text-center max-w-3xl mx-auto relative z-10">
          <h1 className="text-3xl md:text-5xl font-bold leading-snug">
            <span className="text-white">
              매초마다 쏟아지는 공시,
              <br />
              사람이 다 읽고 판단하기엔 한계가 있습니다.
            </span>
          </h1>
          <p className="text-xl md:text-2xl font-bold text-[var(--accent-mint)] mt-6">
            <span className="text-white">DartPR</span>가 해결합니다.
          </p>
          <p className="text-base md:text-lg text-[var(--text-secondary)] mt-3 max-w-xl mx-auto">
            AI 분석으로 공시가 뜨는 순간 바로 핵심을 파악하세요.
          </p>
          <div className="flex items-center justify-center gap-4 mt-8">
            <Link href="/live" className="btn-primary flex items-center gap-2">
              실시간 피드 보기 <ArrowRight size={16} />
            </Link>
            <Link href="/pricing" className="btn-outline">
              플랜 보기
            </Link>
          </div>
        </div>
      </section>

      <section className="py-20 px-4 max-w-5xl mx-auto w-full">
        <div className="grid md:grid-cols-3 gap-6">
          {features.map((f, i) => (
            <div key={i} className="card p-6 text-left">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[var(--accent-mint)]/10 text-[var(--accent-mint)] mb-4">
                {f.icon}
              </div>
              <h3 className="text-base font-bold text-white mb-2 leading-snug">{f.title}</h3>
              <p className="text-sm text-[var(--text-secondary)] leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="py-20 px-4 max-w-5xl mx-auto w-full" id="pricing">
        <h2 className="text-2xl font-bold text-center text-white mb-4">
          플랜
        </h2>
        <p className="text-sm text-[var(--text-secondary)] text-center mb-10 max-w-md mx-auto">
          결제는 카카오톡 오픈프로필로 문의 주시면 관리자가 수동으로 플랜을 변경해드립니다.
        </p>
        <PricingTable />
      </section>
    </div>
  );
}
