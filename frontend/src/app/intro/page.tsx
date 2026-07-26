"use client";

import Link from "next/link";
import {
  Zap, BarChart3, Search, Shield, Brain, Clock, ArrowRight,
  TrendingUp, FileText, Activity, ChevronRight, AlertTriangle, Target
} from "lucide-react";

const problems = [
  {
    icon: AlertTriangle,
    title: "쏟아지는 공시 홍수",
    desc: "하루에도 수백 건의 공시가 발표되지만, 일일이 읽고 분석하는 것은 현실적으로 불가능합니다.",
  },
  {
    icon: FileText,
    title: "읽어도 모르는 원문",
    desc: "공시 원문은 법률 용어와 형식적인 문구로 가득해, 그 내용이 실제로 어떤 의미인지 일반인이 파악하기 어렵습니다.",
  },
  {
    icon: Clock,
    title: "시간과의 싸움",
    desc: "전문 분석가도 공시 하나당 평균 10분 이상 소요됩니다. 그 사이 중요한 신호를 놓칩니다.",
  },
];

const features = [
  {
    icon: Zap,
    title: "실시간 공시 수집",
    desc: "OpenDART API와 30초 간격 폴링으로 공시가 올라오는 즉시 캡처합니다. 놓치는 공시 없이 모든 신호를 포착하세요.",
    color: "text-blue-400",
    bg: "bg-blue-900/10",
    border: "border-blue-900/30",
  },
  {
    icon: Brain,
    title: "AI 자동 분류 + 분석",
    desc: "카테고리 분류, 키워드 추출, DVI 점수 산출까지 1초 미만. 공시가 어떤 성격인지 한눈에 파악하세요.",
    color: "text-purple-400",
    bg: "bg-purple-900/10",
    border: "border-purple-900/30",
  },
  {
    icon: Target,
    title: "DVI 중요도 점수",
    desc: "0~100점으로 공시의 중요도와 정보량을 정량화. 점수가 높을수록 내용이 풍부하거나 이례적인 공시입니다.",
    color: "text-green-400",
    bg: "bg-green-900/10",
    border: "border-green-900/30",
  },
  {
    icon: Shield,
    title: "위험 공시 즉시 탐지",
    desc: "횡령·상장폐지·회생절차 등 리스크 공시를 패턴 매칭으로 즉시 식별. 들어가자마자 빨간불이 켜집니다.",
    color: "text-red-400",
    bg: "bg-red-900/10",
    border: "border-red-900/30",
  },
  {
    icon: Brain,
    title: "AI가 써주는 요약",
    desc: "공시 원문을 AI가 읽고 핵심만 2~3문장으로 요약. 긴 원문을 일일이 읽지 않고도 공시의 핵심을 파악하세요.",
    color: "text-teal-400",
    bg: "bg-teal-900/10",
    border: "border-teal-900/30",
  },
  {
    icon: Search,
    title: "정밀 히스토리 검색",
    desc: "종목코드·회사명·카테고리·점수·날짜·리스크 등 8개 필터로 원하는 공시를 즉시 찾으세요.",
    color: "text-yellow-400",
    bg: "bg-yellow-900/10",
    border: "border-yellow-900/30",
  },
];

const steps = [
  { num: "01", title: "공시 수집", desc: "OpenDART에서 새로운 공시를 30초 간격으로 24시간 자동 수집합니다.", icon: FileText },
  { num: "02", title: "AI 분석",     desc: "카테고리 분류 → 키워드 분석 → DVI 점수 산출 → 위험 탐지까지 1초 미만.", icon: Brain },
  { num: "03", title: "실시간 전달", desc: "점수와 함께 실시간 피드에 즉시 노출. 80점↑ 고impact 공시는 LLM 요약까지 자동 생성.", icon: Zap },
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
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-red-900/10 border border-red-900/30 text-xs text-red-400 font-semibold mb-6">
            <AlertTriangle size={12} />
            당신은 오늘도 수백 건의 공시를 놓치고 있습니다
          </div>

          <h1 className="text-4xl md:text-6xl font-bold text-white leading-tight tracking-tight">
            쏟아지는 공시,<br />
            <span className="text-[var(--accent-mint)]">AI가 먼저 읽고 구조화합니다</span>
          </h1>

          <p className="text-lg text-[var(--text-secondary)] mt-6 max-w-xl leading-relaxed">
            DartPR은 모든 OpenDART 공시를 실시간 수집하고 AI가 분석합니다.
            카테고리 분류, 중요도 점수, 위험 탐지로 단 한 건의 핵심 공시도 놓치지 마세요.
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

        </div>
      </section>

      {/* ── Problem ────────────────────────────────────────── */}
      <section className="border-b border-[var(--border-color)]">
        <div className="max-w-5xl mx-auto px-4 py-20">
          <div className="text-center mb-12">
            <h2 className="text-2xl md:text-3xl font-bold text-white">
              공시 분석, 왜 어려운가요?
            </h2>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {problems.map((p) => (
              <div key={p.title} className="card p-6 text-center">
                <div className="w-12 h-12 rounded-xl bg-red-900/10 flex items-center justify-center mx-auto mb-4">
                  <p.icon size={24} className="text-red-400" />
                </div>
                <h3 className="text-base font-bold text-white mb-2">{p.title}</h3>
                <p className="text-sm text-[var(--text-secondary)] leading-relaxed">{p.desc}</p>
              </div>
            ))}
          </div>
          <div className="text-center mt-8">
            <Link href="/live" className="text-sm text-[var(--accent-mint)] hover:text-white transition-colors inline-flex items-center gap-1">
              DartPR이 해결하는 방법 보기
              <ChevronRight size={14} />
            </Link>
          </div>
        </div>
      </section>

      {/* ── How it works ──────────────────────────────────── */}
      <section className="max-w-5xl mx-auto px-4 py-20">
        <div className="text-center mb-12">
          <h2 className="text-2xl md:text-3xl font-bold text-white">3초면 완료되는 분석</h2>
          <p className="text-sm text-[var(--text-secondary)] mt-2">
            분석가가 10분 걸릴 일을 DartPR은 1초면 끝냅니다
          </p>
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
            오늘부터 공시를 AI에게 맡기세요
          </h2>
          <p className="text-sm text-[var(--text-secondary)] mt-2 max-w-lg mx-auto">
            가입 없이도 실시간 피드를 확인할 수 있습니다. Pro 플랜으로 업그레이드하면
            3초 지연 없이 모든 공시를 실시간으로 받아보고, 놓친 공시는 다시 확인하세요.
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
          <p className="text-xs text-[var(--text-muted)] mt-6">
            더 이상 하루에도 수백 건 쏟아지는 공시 원문을 일일이 읽지 마세요.
            DartPR이 먼저 읽고, 분석하고, 알려드립니다.
          </p>
        </div>
      </section>

    </div>
  );
}
