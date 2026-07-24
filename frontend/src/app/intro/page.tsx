"use client";

import Link from "next/link";
import {
  Zap, BarChart3, Search, Shield, Brain, Clock, ArrowRight,
  TrendingUp, FileText, Activity, ChevronRight
} from "lucide-react";

const features = [
  {
    icon: Zap,
    title: "실시간 공시 수집",
    desc: "OpenDART API와 30초 간격 폴링으로 공시가 올라오는 즉시 캡처합니다.",
    color: "text-blue-400",
    bg: "bg-blue-900/10",
    border: "border-blue-900/30",
  },
  {
    icon: Brain,
    title: "AI 카테고리 분류",
    desc: "7개 카테고리로 자동 분류. 자금조달, 바이오, 실적, 주주환원 등 원하는 공시만 골라보세요.",
    color: "text-purple-400",
    bg: "bg-purple-900/10",
    border: "border-purple-900/30",
  },
  {
    icon: BarChart3,
    title: "DVI 스코어링",
    desc: "0~100점 DVI 점수로 공시의 중요도를 한눈에. 90점 이상은 강력한 호재 신호입니다.",
    color: "text-green-400",
    bg: "bg-green-900/10",
    border: "border-green-900/30",
  },
  {
    icon: Shield,
    title: "위험 공시 탐지",
    desc: "FAST-FAIL 패턴 매칭으로 횡령·상폐·회생 등 위험 공시를 즉시 식별합니다.",
    color: "text-red-400",
    bg: "bg-red-900/10",
    border: "border-red-900/30",
  },
  {
    icon: FileText,
    title: "AI 요약",
    desc: "80점 이상 공시는 Groq LLM이 핵심만 요약. 긴 원문을 3초 만에 파악하세요.",
    color: "text-teal-400",
    bg: "bg-teal-900/10",
    border: "border-teal-900/30",
  },
  {
    icon: Search,
    title: "히스토리 검색",
    desc: "종목코드·회사명·카테고리·점수·날짜·리스크 등 8개 필터로 정밀 검색.",
    color: "text-yellow-400",
    bg: "bg-yellow-900/10",
    border: "border-yellow-900/30",
  },
];

const steps = [
  { num: "01", title: "공시 수집", desc: "OpenDART에서 새로운 공시를 30초 간격으로 자동 수집합니다.", icon: FileText },
  { num: "02", title: "AI 분석", desc: "카테고리 분류 → 키워드 추출 → DVI 점수 산출까지 1초 미만.", icon: Brain },
  { num: "03", title: "실시간 전달", desc: "점수와 함께 실시간 피드에 노출. 80점↑은 LLM 요약까지 제공.", icon: Zap },
];

const stats = [
  { label: "실시간 공시", value: "390+" },
  { label: "분석 커버리지", value: "7개 카테고리" },
  { label: "평균 분석 시간", value: "< 1초" },
  { label: "업데이트 주기", value: "30초" },
];

export default function IntroPage() {
  return (
    <div className="min-h-screen">
      {/* ── Hero ───────────────────────────────────────────── */}
      <section className="relative overflow-hidden border-b border-[var(--border-color)]">
        {/* Background glow */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] rounded-full bg-[var(--accent-mint)]/5 blur-[120px]" />
          <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-purple-500/5 blur-[100px]" />
        </div>

        <div className="max-w-5xl mx-auto px-4 py-20 md:py-28 relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[var(--accent-mint)]/5 border border-[var(--accent-mint)]/20 text-xs text-[var(--accent-mint)] font-semibold mb-6">
            <Activity size={12} />
            AI 기반 공시 분석 플랫폼
          </div>

          <h1 className="text-4xl md:text-6xl font-bold text-white leading-tight tracking-tight">
            매초 쏟아지는 공시,<br />
            <span className="text-[var(--accent-mint)]">AI가 먼저 읽습니다</span>
          </h1>

          <p className="text-lg text-[var(--text-secondary)] mt-4 max-w-xl leading-relaxed">
            DartPR은 OpenDART 공시를 실시간으로 수집하고 AI가 분석합니다.
            중요도 점수와 리스크 탐지로 핵심 공시를 놓치지 마세요.
          </p>

          <div className="flex items-center gap-4 mt-8">
            <Link href="/live" className="btn-primary text-sm flex items-center gap-2">
              실시간 피드 보기
              <ArrowRight size={14} />
            </Link>
            <Link href="/pricing" className="btn-outline text-sm">
              플랜 보기
            </Link>
          </div>

          {/* Stats row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mt-16 p-6 rounded-2xl bg-[var(--bg-card)]/50 border border-[var(--border-color)]">
            {stats.map((s) => (
              <div key={s.label} className="text-center">
                <div className="text-2xl font-bold text-white">{s.value}</div>
                <div className="text-xs text-[var(--text-muted)] mt-1">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ──────────────────────────────────── */}
      <section className="max-w-5xl mx-auto px-4 py-20">
        <div className="text-center mb-12">
          <h2 className="text-2xl md:text-3xl font-bold text-white">How it works</h2>
          <p className="text-sm text-[var(--text-secondary)] mt-2">3단계로 끝나는 공시 분석</p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {steps.map((step, i) => (
            <div key={step.num} className="card p-6 relative">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg bg-[var(--accent-mint)]/10 flex items-center justify-center">
                  <step.icon size={20} className="text-[var(--accent-mint)]" />
                </div>
                <span className="text-2xl font-bold text-[var(--text-muted)] font-mono">{step.num}</span>
              </div>
              <h3 className="text-lg font-bold text-white">{step.title}</h3>
              <p className="text-sm text-[var(--text-secondary)] mt-2 leading-relaxed">{step.desc}</p>
              {i < steps.length - 1 && (
                <ChevronRight size={20} className="hidden md:block absolute -right-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
              )}
            </div>
          ))}
        </div>
      </section>

      {/* ── Features ──────────────────────────────────────── */}
      <section className="border-t border-[var(--border-color)]">
        <div className="max-w-5xl mx-auto px-4 py-20">
          <div className="text-center mb-12">
            <h2 className="text-2xl md:text-3xl font-bold text-white">핵심 기능</h2>
            <p className="text-sm text-[var(--text-secondary)] mt-2">DartPR이 제공하는 모든 분석 도구</p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {features.map((f) => (
              <div
                key={f.title}
                className={`card p-5 border ${f.border} hover:border-[var(--text-muted)] transition-all`}
              >
                <div className={`w-10 h-10 rounded-lg ${f.bg} flex items-center justify-center mb-3`}>
                  <f.icon size={20} className={f.color} />
                </div>
                <h3 className="text-sm font-bold text-white">{f.title}</h3>
                <p className="text-xs text-[var(--text-secondary)] mt-1.5 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ────────────────────────────────────────────── */}
      <section className="border-t border-[var(--border-color)]">
        <div className="max-w-3xl mx-auto px-4 py-20 text-center">
          <h2 className="text-2xl md:text-3xl font-bold text-white">
            지금 바로 시작하세요
          </h2>
          <p className="text-sm text-[var(--text-secondary)] mt-2 max-w-md mx-auto">
            가입 없이도 실시간 공시를 확인할 수 있습니다.
            Pro 플랜으로 전환하면 지연 없이 모든 공시를 받아보세요.
          </p>
          <div className="flex items-center justify-center gap-4 mt-8">
            <Link href="/live" className="btn-primary text-sm flex items-center gap-2">
              <Zap size={14} />
              실시간 피드
            </Link>
            <Link href="/signup" className="btn-outline text-sm">
              회원가입
            </Link>
          </div>
        </div>
      </section>

      {/* ── Footer ────────────────────────────────────────── */}
      <footer className="border-t border-[var(--border-color)] py-8">
        <div className="max-w-5xl mx-auto px-4 flex items-center justify-between">
          <span className="text-sm font-bold">
            <span className="text-[var(--accent-mint)]">Dart</span>
            <span className="text-white">PR</span>
          </span>
          <span className="text-xs text-[var(--text-muted)]">
            DartPR © 2026 · 데이터 출처: OpenDART
          </span>
        </div>
      </footer>
    </div>
  );
}
