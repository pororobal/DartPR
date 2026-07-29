"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ChevronRight, Check, Zap, BarChart3, Search, Shield, Brain,
  ArrowRight, Sparkles, Target, Filter, Crown, X
} from "lucide-react";

const STEPS = [
  {
    title: "DartPR에 오신 걸 환영합니다",
    subtitle: "AI가 DART 공시를 실시간 분석합니다",
    content: (
      <div className="space-y-6 text-center">
        <div className="w-20 h-20 rounded-2xl bg-[var(--accent-mint)]/10 flex items-center justify-center mx-auto">
          <Zap size={40} className="text-[var(--accent-mint)]" />
        </div>
        <p className="text-[var(--text-secondary)] text-sm leading-relaxed max-w-md mx-auto">
          DartPR은 OpenDART의 모든 공시를 30초 간격으로 수집하고,
          AI가 카테고리 분류·정보량 점수 산출·위험 탐지를 자동으로 수행합니다.
          <br /><br />
          하루 수백 건의 공시 중 <span className="text-white font-semibold">시세에 영향을 주는 핵심 공시만</span> 선별하여
          실시간 피드로 보여드립니다.
        </p>
      </div>
    ),
  },
  {
    title: "실시간 피드 — 공시를 한눈에",
    subtitle: "DVI 점수와 함께 정렬된 핵심 공시",
    content: (
      <div className="space-y-5">
        {/* DVI score explanation */}
        <div className="card p-4 border border-[var(--border-color)]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-green-900/10 flex items-center justify-center">
              <Target size={20} className="text-green-400" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-white">DVI 점수</span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-purple-900/20 text-purple-400">정보량 지수</span>
              </div>
              <p className="text-xs text-[var(--text-secondary)] mt-1">
                0~100점. 점수가 높을수록 정보량이 많고 시장에 새로운 정보를 제공하는 공시입니다.
              </p>
            </div>
          </div>
          <div className="grid grid-cols-5 gap-1 mt-4">
            {[
              { range: "0~20", label: "리스크", color: "bg-red-500", text: "text-red-400" },
              { range: "21~40", label: "저영향", color: "bg-orange-500", text: "text-orange-300" },
              { range: "41~60", label: "보통", color: "bg-yellow-500", text: "text-yellow-400" },
              { range: "61~80", label: "주목", color: "bg-lime-500", text: "text-lime-400" },
              { range: "81~100", label: "고영향", color: "bg-green-500", text: "text-green-400" },
            ].map((s) => (
              <div key={s.range} className="text-center">
                <div className={`h-1.5 rounded-full ${s.color} opacity-80`} />
                <div className={`text-[10px] font-bold mt-1 ${s.text}`}>{s.range}</div>
                <div className="text-[9px] text-[var(--text-muted)]">{s.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Signal badges */}
        <div className="card p-4 border border-[var(--border-color)]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-900/10 flex items-center justify-center">
              <Filter size={20} className="text-blue-400" />
            </div>
            <div className="flex-1 min-w-0">
              <span className="text-sm font-bold text-white">카테고리·시그널 배지</span>
              <p className="text-xs text-[var(--text-secondary)] mt-1">
                각 공시는 카테고리(주주환원·바이오·자금조달·실적 등)와
                시그널(긍정/부정/위험) 배지로 구분됩니다. 필터 탭으로 긍정/부정만 골라볼 수 있습니다.
              </p>
            </div>
          </div>
        </div>

        {/* 3-min delay */}
        <div className="card p-4 border border-yellow-900/30 bg-yellow-900/5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-yellow-900/10 flex items-center justify-center">
              <Crown size={20} className="text-yellow-400" />
            </div>
            <div className="flex-1 min-w-0">
              <span className="text-sm font-bold text-white">무료: 3분 지연</span>
              <p className="text-xs text-[var(--text-secondary)] mt-1">
                Free 플랜은 3분 지연된 피드를 볼 수 있습니다. Pro로 업그레이드하면 지연 없이 실시간으로 확인 가능합니다.
              </p>
            </div>
          </div>
        </div>
      </div>
    ),
  },
  {
    title: "AI 분석 요약",
    subtitle: "LLM이 읽어주는 핵심 요약",
    content: (
      <div className="space-y-5">
        <div className="card p-4 border border-[var(--border-color)]">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-lg bg-teal-900/10 flex items-center justify-center shrink-0">
              <Brain size={20} className="text-teal-400" />
            </div>
            <div className="flex-1 min-w-0">
              <span className="text-sm font-bold text-white">AI 요약</span>
              <p className="text-xs text-[var(--text-secondary)] mt-1 leading-relaxed">
                각 공시 카드 하단에 LLM이 생성한 2~3문장 요약이 표시됩니다.
                공시 원문의 핵심 수치·절차·일정을 사실 위주로 요약하며,
                주가 예측이나 호재/악재 판단을 포함하지 않습니다.
              </p>
              <div className="mt-3 p-3 rounded-lg bg-[var(--bg-hover)] border border-[var(--border-color)]">
                <div className="flex items-center gap-2 mb-2">
                  <Sparkles size={12} className="text-[var(--accent-mint)]" />
                  <span className="text-[10px] font-bold text-[var(--accent-mint)] uppercase tracking-wider">AI 요약 예시</span>
                </div>
                <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                  NAVER는 보통주 4,901,094주(전체의 3.1%)를 8월 3일 자사주 소각하기로 이사회 결의했다.
                  배당가능이익 범위 내 진행으로 자본금 감소는 없으며, 자기주식 소각은 주주가치 제고를 위한 결정이다.
                  일회성 이벤트, 단기 영향.
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="card p-4 border border-[var(--border-color)]">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-lg bg-red-900/10 flex items-center justify-center shrink-0">
              <Shield size={20} className="text-red-400" />
            </div>
            <div className="flex-1 min-w-0">
              <span className="text-sm font-bold text-white">위험 공시 탐지</span>
              <p className="text-xs text-[var(--text-secondary)] mt-1 leading-relaxed">
                횡령·상장폐지·회생절차·무상감자 등 리스크 공시는 패턴 매칭으로 즉시 식별됩니다.
                피드 상단에 빨간색 경고 배지와 함께 표시되며, DVI 점수는 0점입니다.
                들어가자마자 빨간불이 켜지므로 절대 놓치지 않습니다.
              </p>
            </div>
          </div>
        </div>
      </div>
    ),
  },
  {
    title: "히스토리 검색",
    subtitle: "8개 필터로 원하는 공시를 즉시 검색",
    content: (
      <div className="space-y-5">
        <div className="card p-4 border border-[var(--border-color)]">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-lg bg-purple-900/10 flex items-center justify-center shrink-0">
              <Search size={20} className="text-purple-400" />
            </div>
            <div className="flex-1 min-w-0">
              <span className="text-sm font-bold text-white">정밀 검색 필터</span>
              <p className="text-xs text-[var(--text-secondary)] mt-1 leading-relaxed">
                종목코드·회사명·카테고리·DVI 점수 범위·날짜·리스크 플래그 등
                8개 필터를 조합하여 원하는 공시를 즉시 찾을 수 있습니다.
                Pro 플랜에서는 DVI 히스토리 차트와 고급 알림 기능도 사용 가능합니다.
              </p>
            </div>
          </div>
        </div>

        <div className="card p-4 border border-[var(--border-color)]">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-900/10 flex items-center justify-center shrink-0">
              <BarChart3 size={20} className="text-blue-400" />
            </div>
            <div className="flex-1 min-w-0">
              <span className="text-sm font-bold text-white">검색 가능한 카테고리</span>
              <div className="flex flex-wrap gap-1.5 mt-2">
                {["주주환원", "자금조달", "실적", "바이오", "영업계약", "지배구조", "리스크"].map((c) => (
                  <span key={c} className="text-[10px] font-bold px-2 py-0.5 rounded bg-[var(--bg-hover)] text-[var(--text-secondary)] border border-[var(--border-color)]">
                    {c}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    ),
  },
  {
    title: "Pro 플랜으로 업그레이드",
    subtitle: "더 빠르게, 더 많이",
    content: (
      <div className="space-y-5">
        <div className="card p-6 border border-[var(--accent-mint)] ring-1 ring-[var(--accent-mint)]">
          <span className="text-[10px] font-bold text-[var(--accent-mint)] uppercase tracking-wider mb-3 block">추천</span>

          <div className="space-y-4">
            {[
              { label: "실시간 피드", free: "3분 지연", pro: "지연 없음" },
              { label: "히스토리 검색", free: "전체", pro: "전체 + 차트" },
              { label: "AI 분석 요약", free: "제공", pro: "제공" },
              { label: "DVI 히스토리 차트", free: "—", pro: "✅" },
              { label: "고급 알림", free: "—", pro: "✅" },
            ].map((row) => (
              <div key={row.label} className="flex items-center justify-between py-1">
                <span className="text-xs text-[var(--text-secondary)]">{row.label}</span>
                <div className="flex items-center gap-3 text-xs">
                  <span className="text-[var(--text-muted)]">{row.free}</span>
                  <ChevronRight size={12} className="text-[var(--text-muted)]" />
                  <span className="text-green-400 font-semibold">{row.pro}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <p className="text-xs text-[var(--text-secondary)] text-center">
          Pro 플랜은 카카오톡 문의를 통해 가입할 수 있습니다.
        </p>

        <div className="flex items-center justify-center gap-3">
          <Link
            href="/pricing"
            className="btn-outline text-sm flex items-center gap-2"
          >
            <Crown size={14} className="text-yellow-400" />
            플랜 보기
          </Link>
        </div>
      </div>
    ),
  },
];

export default function OnboardingPage() {
  const [step, setStep] = useState(0);
  const router = useRouter();

  const current = STEPS[step];
  const isLast = step === STEPS.length - 1;

  const handleNext = () => {
    if (isLast) {
      router.push("/live");
    } else {
      setStep(step + 1);
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-lg">
        {/* Progress bar */}
        <div className="flex items-center gap-2 mb-8">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className={`h-1 flex-1 rounded-full transition-all duration-500 ${
                i <= step ? "bg-[var(--accent-mint)]" : "bg-[var(--border-color)]"
              }`}
            />
          ))}
        </div>

        {/* Step counter */}
        <div className="text-center mb-8">
          <span className="text-xs font-bold text-[var(--accent-mint)] tracking-widest uppercase">
            {step + 1} / {STEPS.length}
          </span>
        </div>

        {/* Title */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-white">{current.title}</h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">{current.subtitle}</p>
        </div>

        {/* Content */}
        <div className="min-h-[320px]">
          {current.content}
        </div>

        {/* Navigation */}
        <div className="flex items-center justify-between mt-10">
          {step > 0 ? (
            <button
              onClick={() => setStep(step - 1)}
              className="btn-outline text-sm"
            >
              이전
            </button>
          ) : (
            <div />
          )}

          <button
            onClick={handleNext}
            className="btn-primary text-sm flex items-center gap-2"
          >
            {isLast ? (
              <>실시간 피드 시작하기 <ArrowRight size={14} /></>
            ) : (
              <>다음 <ChevronRight size={14} /></>
            )}
          </button>
        </div>

        {/* Skip */}
        {!isLast && (
          <div className="text-center mt-4">
            <button
              onClick={() => router.push("/live")}
              className="text-xs text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors"
            >
              건너뛰기
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
