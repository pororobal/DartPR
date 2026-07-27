"use client";

import Link from "next/link";
import {
  Zap, BarChart3, Search, Shield, Brain, Clock, ArrowRight,
  TrendingUp, FileText, Activity, ChevronRight, AlertTriangle, Target,
  Filter, Sparkles, PieChart
} from "lucide-react";

// ─── Real examples from today's feed ──────────────────────────

interface ExampleCardProps {
  ticker: string;
  company: string;
  time: string;
  title: string;
  score: number;
  signal: { icon: string; label: string; color: string };
  summary: string;
  badge: string;
}

const examples: ExampleCardProps[] = [
  {
    ticker: "035420",
    company: "NAVER",
    time: "07. 27. 오후 04:50",
    title: "주식소각결정",
    score: 90,
    signal: { icon: "🟢", label: "단기 긍정 신호", color: "text-green-400" },
    summary: "NAVER는 보통주 4,901,094주(전체의 3.1%)를 8월 3일 자사주 소각하기로 이사회 결의했다. 배당가능이익 범위 내 진행으로 자본금 감소는 없으며, 주당 가치에 긍정적인 영향을 미칠 수 있다.",
    badge: "주주환원",
  },
  {
    ticker: "185750",
    company: "종근당",
    time: "07. 27. 오후 06:27",
    title: "CKD-339 식약처 3상 임상시험 계획 승인",
    score: 95,
    signal: { icon: "🟢", label: "장기 긍정 신호", color: "text-green-400" },
    summary: "종근당은 고혈압 치료제 CKD-339에 대해 식약처가 제3상 임상시험 계획을 승인했다. 300명 대상 36개월 임상 돌입. 신약 개발 본궤도 진입으로 장기 사업 성장에 기여할 구조적 이벤트.",
    badge: "바이오",
  },
  {
    ticker: "289010",
    company: "아이스크림에듀",
    time: "07. 27. 오후 06:23",
    title: "관리종목지정우려 (시가총액 200억원 미달)",
    score: 8,
    signal: { icon: "🔴", label: "단기 부정 신호", color: "text-red-400" },
    summary: "시가총액 200억원 미달로 관리종목 지정 우려. 상장 유지에 위험이 따르는 신호.",
    badge: "상장위험",
  },
];

// ─── Static content ──────────────────────────────────────────

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
    icon: Filter,
    title: "핵심 공시 선별",
    desc: "시세에 영향을 주는 주목할 만한 공시만 골라서 실시간 피드에 표시. 대량보유신고·일괄신고 등 노이즈는 자동 필터링합니다.",
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
    icon: Sparkles,
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
  { num: "03", title: "실시간 전달", desc: "점수와 함께 실시간 피드에 즉시 노출. 시세에 영향 주는 핵심 공시만 선별하여 보여줍니다.", icon: Filter },
];


// ─── ExampleCard component ────────────────────────────────────

function ExampleCard({ item }: { item: ExampleCardProps }) {
  const barColor =
    item.score >= 90 ? "bg-green-500" :
    item.score >= 70 ? "bg-lime-500" :
    item.score >= 40 ? "bg-yellow-500" :
    item.score > 0   ? "bg-orange-500" : "bg-red-500";

  const scoreTextColor =
    item.score >= 90 ? "text-green-400" :
    item.score >= 70 ? "text-lime-400" :
    item.score >= 40 ? "text-yellow-400" :
    item.score > 0   ? "text-orange-300" : "text-red-400";

  return (
    <div className="card p-4 border border-[var(--border-color)] hover:border-[var(--text-muted)] transition-all">
      {/* Header */}
      <div className="flex items-start gap-3 mb-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-xs font-bold text-[var(--accent-blue)]">[{item.ticker}]</span>
            <span className="text-sm font-semibold text-white">{item.company}</span>
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border border-purple-900/30 text-purple-400 bg-purple-900/10">
              {item.badge}
            </span>
            <span className="text-[10px] text-[var(--text-muted)] ml-auto">{item.time}</span>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1 leading-snug line-clamp-2">{item.title}</p>
        </div>
        {/* DVI */}
        <div className="shrink-0 w-14 text-center">
          <div className="text-[9px] font-mono font-bold text-[var(--text-muted)]">DVI</div>
          <div className={`text-lg font-bold font-mono leading-none ${scoreTextColor}`}>{item.score}</div>
          <div className="w-full h-1 rounded-full bg-gray-800 mt-0.5 overflow-hidden">
            <div className={`h-full rounded-full ${barColor}`} style={{ width: `${item.score}%` }} />
          </div>
        </div>
      </div>
      {/* Signal */}
      <div className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-opacity-20 ${item.signal.color} bg-green-900/10`}>
        <span>{item.signal.icon}</span>
        <span className={item.signal.color}>{item.signal.label}</span>
      </div>
      {/* Summary */}
      <p className="text-xs text-[var(--text-secondary)] mt-2 leading-relaxed border-t border-[var(--border-color)] pt-2">
        {item.summary}
      </p>
    </div>
  );
}


// ─── Page ─────────────────────────────────────────────────────

export default function IntroPage() {
  return (
    <div className="min-h-screen">
      {/* ── Hero ───────────────────────────────────────────── */}
      <section className="relative overflow-hidden border-b border-[var(--border-color)]">
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
            DartPR은 모든 OpenDART 공시를 실시간 수집하고 AI로 분석합니다.
            시세에 영향을 주는 핵심 공시만 선별하여 보여주며,
            카테고리 분류, 중요도 점수, 위험 탐지로 단 한 건의 중요한 신호도 놓치지 않게 도와줍니다.
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

      {/* ── Live examples ─────────────────────────────────── */}
      <section className="border-b border-[var(--border-color)]">
        <div className="max-w-5xl mx-auto px-4 py-20">
          <div className="text-center mb-3">
            <span className="text-xs font-bold text-[var(--accent-mint)] tracking-widest uppercase">실시간 피드 샘플</span>
          </div>
          <h2 className="text-2xl md:text-3xl font-bold text-white text-center mb-2">
            오늘 DART에 올라온 공시 중에서
          </h2>
          <p className="text-sm text-[var(--text-secondary)] text-center mb-10 max-w-lg mx-auto">
            DartPR은 하루 수백 건의 공시 중 시세에 영향을 줄 수 있는 공시만 골라서 보여줍니다.
            아래는 오늘 실시간 피드에 실제로 표시된 공시들입니다.
          </p>

          <div className="grid md:grid-cols-3 gap-4">
            {examples.map((ex) => (
              <ExampleCard key={ex.ticker + ex.title} item={ex} />
            ))}
          </div>

          <div className="flex items-center justify-center gap-2 mt-8 text-xs text-[var(--text-muted)]">
            <Filter size={12} />
            단순 대량보유 신고, 일괄신고추가서류, 채권유동화 등 시세와 무관한 공시는 자동으로 걸러집니다.
          </div>
        </div>
      </section>

      {/* ── How it works ──────────────────────────────────── */}
      <section className="max-w-5xl mx-auto px-4 py-20">
        <div className="text-center mb-3">
          <span className="text-xs font-bold text-[var(--accent-mint)] tracking-widest uppercase">작동 방식</span>
        </div>
        <h2 className="text-2xl md:text-3xl font-bold text-white text-center mb-2">3초면 완료되는 분석</h2>
        <p className="text-sm text-[var(--text-secondary)] text-center mb-12">
          분석가가 10분 걸릴 일을 DartPR은 1초면 끝냅니다
        </p>

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

      {/* ── Problem ────────────────────────────────────────── */}
      <section className="border-t border-b border-[var(--border-color)]">
        <div className="max-w-5xl mx-auto px-4 py-20">
          <div className="text-center mb-3">
            <span className="text-xs font-bold text-[var(--accent-mint)] tracking-widest uppercase">Problem</span>
          </div>
          <h2 className="text-2xl md:text-3xl font-bold text-white text-center mb-10">
            공시 분석, 왜 어려운가요?
          </h2>
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
        </div>
      </section>

      {/* ── Features ──────────────────────────────────────── */}
      <section className="border-b border-[var(--border-color)]">
        <div className="max-w-5xl mx-auto px-4 py-20">
          <div className="text-center mb-3">
            <span className="text-xs font-bold text-[var(--accent-mint)] tracking-widest uppercase">Features</span>
          </div>
          <h2 className="text-2xl md:text-3xl font-bold text-white text-center mb-2">핵심 기능</h2>
          <p className="text-sm text-[var(--text-secondary)] text-center mb-10">DartPR이 제공하는 모든 분석 도구</p>

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
      <section>
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
            DartPR이 먼저 읽고, 분석하고, 골라서 알려드립니다.
          </p>
        </div>
      </section>

    </div>
  );
}
