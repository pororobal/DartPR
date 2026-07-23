"use client";

import Link from "next/link";
import { Sparkles, Zap, TrendingUp, ArrowRight } from "lucide-react";
import PricingTable from "@/components/PricingTable";

const features = [
  {
    icon: <Sparkles size={24} />,
    title: "LLM 분석",
    desc: "Groq 기반 LLM이 DART 공시 원문을 즉시 분석, 카테고리 분류와 트랩 여부를 판별합니다.",
  },
  {
    icon: <Zap size={24} />,
    title: "실시간 Realtime 전송",
    desc: "Supabase Realtime으로 새 공시가 등록되는 즉시 브라우저로 푸시됩니다.",
  },
  {
    icon: <TrendingUp size={24} />,
    title: "DVI 점수",
    desc: "데이터 기반 규칙엔진이 공시의 주가 영향을 0-100 점수로 정량화합니다.",
  },
];

export default function LandingPage() {
  return (
    <div>
      <section className="relative min-h-[80vh] flex items-center justify-center px-4">
        <div className="absolute inset-0 bg-gradient-to-b from-[var(--accent-mint)]/5 to-transparent pointer-events-none" />
        <div className="text-center max-w-3xl mx-auto relative z-10">
          <h1 className="text-4xl md:text-6xl font-bold leading-tight">
            <span className="text-[var(--accent-mint)]">DART</span>0s
            <br />
            <span className="text-white">실시간 공시를</span>
            <br />
            <span className="text-white">트레이더의 눈으로</span>
          </h1>
          <p className="text-lg text-[var(--text-secondary)] mt-6 max-w-xl mx-auto">
            DART 공시를 LLM이 분석하고 DVI 점수로 환산합니다.
            <br />
            더 이상 수백 건의 공시를 일일이 읽지 마세요.
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

      <section className="py-20 px-4 max-w-6xl mx-auto">
        <h2 className="text-2xl font-bold text-center text-white mb-12">
          DART0s가 해결합니다
        </h2>
        <div className="grid md:grid-cols-3 gap-6">
          {features.map((f, i) => (
            <div key={i} className="card p-6 text-center">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[var(--accent-mint)]/10 text-[var(--accent-mint)] mb-4">
                {f.icon}
              </div>
              <h3 className="text-lg font-bold text-white mb-2">{f.title}</h3>
              <p className="text-sm text-[var(--text-secondary)]">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="py-20 px-4" id="pricing">
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
