"use client";

import { useState } from "react";
import { DisclosureItem, disclosures } from "@/lib/api";
import { ExternalLink, Info, Clock, Sparkles } from "lucide-react";

interface DisclosureCardProps {
  item: DisclosureItem;
  isAdmin?: boolean;
}

// ─── Category helpers ─────────────────────────────────────────

const categoryChip: Record<string, { label: string; color: string }> = {
  ADMINISTRATIVE:    { label: "행정",       color: "border-gray-600 text-gray-400" },
  CAPITAL_RAISING:   { label: "자금조달",   color: "border-blue-600 text-blue-400" },
  BIOTECH:           { label: "바이오",     color: "border-green-600 text-green-400" },
  BUSINESS_CONTRACT: { label: "영업계약",   color: "border-purple-600 text-purple-400" },
  EARNINGS:          { label: "실적",       color: "border-yellow-600 text-yellow-400" },
  SHAREHOLDER_RETURN:{ label: "주주환원",   color: "border-teal-600 text-teal-400" },
  DELISTING_RISK:    { label: "상장위험",   color: "border-red-600 text-red-400" },
};

// ─── Signal helpers ───────────────────────────────────────────

// 카테고리 → signal badge label (이벤트 성격 표기)
const CATEGORY_SIGNAL_LABELS: Record<string, string> = {
  "CAPITAL_RAISING":   "자본조달",
  "BIOTECH":           "임상 이벤트",
  "BUSINESS_CONTRACT": "계약 이벤트",
  "EARNINGS":          "실적",
  "SHAREHOLDER_RETURN":"주주환원",
  "DELISTING_RISK":    "상장유지 리스크",
};

// sub_rule_id → 사람이 읽을 수 있는 설명 (부정/긍정 이유)
const SUB_RULE_DESC: Record<string, string> = {
  // ── NEGATIVE ──
  "MA_MANAGEMENT_DISPUTE":                "경영권 분쟁 — 이사회 분열, 의사결정 지연 상태",
  "MA_MAJOR_CHANGE_NEWLY_FORMED":         "설립 1년 미만 법인으로 최대주주 변경 — 경영 이력 부족",
  "MA_BLOCK_TRADE":                       "최대주주 장내매도 — 지분 매각",
  "BIOTECH_CLINICAL_HOLD":               "임상 중지 — 바이오 파이프라인 진행 중단",
  "BIOTECH_TECH_RETURN":                  "기술반환/라이선스 해지 — 계약 해지",
  "CAPITAL_RAISING_FREE_REDUCTION":       "무상감자 — 주식 수 감소, 액면가 하향 조정",
  "BUSINESS_CONTRACT_TERMINATED":         "공급계약 해지 — 계약 종료",
  "BUSINESS_CONTRACT_MODIFIED":           "공급계약 변경/감액 — 계약 조건 변동",
  "EARNINGS_PROFIT_TO_LOSS_NO_HISTORY":   "적자전환 — 당기순손실 기록",
  "EARNINGS_REVENUE_DECREASE":            "매출 감소 — 전기 대비 매출액 하락",
  "EARNINGS_LOSS_CONTINUED":              "적자 지속 — 당기순손실 지속",
  "SHAREHOLDER_DISPOSAL_OPERATING":       "자사주 처분 — 보유 자사주 매각",
  "SHAREHOLDER_DISPOSAL_STOCK_OPTION":    "자사주 처분(스톡옵션) — 스톡옵션 행사에 따른 처분",
  "MA_SPLIT_WITH_LISTING":               "물적분할 후 자회사 상장 — 분할 설립",
  "CAPITAL_RAISING_CB_WORKING":           "운영자금 조달 CB — 운영 목적 자금 조달",
  "CAPITAL_RAISING_DELAYED_PAYMENT":      "납입 지연 — 자금 납입 기한 미준수",
  "CAPITAL_RAISING_CB_REFIXING":          "CB 전환가액 하향 조정 — 전환 조건 변경",
  "CAPITAL_RAISING_WITHDRAWN":            "유상증자 철회 — 증자 계획 취소",
  "CAPITAL_RAISING_CB_CONVERTED":         "CB 전환청구권 행사 — 신주 발행",
  "CAPITAL_RAISING_WARRANT_EXERCISED":    "신주인수권 행사 — 신주 발행",
  "SHAREHOLDER_TREASURY_COLLATERAL":      "자사주 담보 제공 — 자사주 질권 설정",
  "SHAREHOLDER_MAJOR_PLEDGE":             "최대주주 지분 담보 — 대주주 보유 지분 질권 설정",
  "SHAREHOLDER_STOCK_DIVIDEND":           "주식배당 — 현금 대신 주식 지급",
  "MA_DEBT_TO_EQUITY":                    "출자전환 — 채무를 지분으로 전환",
  "MA_DEBT_FORGIVENESS":                  "채무 면제/재조정 — 채무 조건 변경",
  "EARNINGS_LOSS_TO_PROFIT_NON_OP":       "영업외손익으로 흑자전환 — 영업손실, 영업외수익 발생",
  "EARNINGS_OP_PROFIT_WORSENING":         "영업이익 악화 — 전기 대비 영업이익 감소",
  "EARNINGS_PROFIT_TO_LOSS_1Q":           "1분기 만에 적자전환 — 분기 기준 손실 전환",
  "EARNINGS_PROFIT_TO_LOSS_3Q":           "3분기 연속 흑자→적자 — 분기 기준 손실 지속",
  "EARNINGS_LOSS_CONTINUED_4Q":           "4분기 연속 적자 — 분기 기준 손실 장기화",
  "RISK_GOING_CONCERN":                   "계속기업 불확실성 — 존속 능력에 대한 검토 의견",
  "RISK_CAPITAL_IMPAIRMENT":              "자본잠식 — 자본총계가 자본금 미달",
  "RISK_MANAGEMENT_ISSUE":                "관리종목 지정 — 상장 유지 요건 심사 대상",
  "RISK_LISTING_REVIEW":                  "상장적격성 심사 — 상장폐지 심사 대상",
  "BUSINESS_CONTRACT_NA_PCT":             "공급계약 체결(매출액 대비 비율 미공개) — 규모 확인 불가",

  // ── POSITIVE ──
  "BIOTECH_FDA_APPROVAL":                 "FDA/식약처 승인 — 임상/판매 승인 획득",
  "BIOTECH_TECH_TRANSFER_AMOUNT":         "기술이전 계약 체결(규모 공개) — 기술 수출 계약",
  "BIOTECH_PHASE3_NDA":                   "임상 3상/품목허가 신청 — 규제 승인 신청 완료",
  "SHAREHOLDER_FIRST_BUYBACK_CANCEL":     "최초 자사주 취득+소각 — 주주환원 결정",
  "SHAREHOLDER_REPEAT_BUYBACK_CANCEL":    "반복 자사주 소각 — 주주환원 정책",
  "SHAREHOLDER_TRIVIAL_CANCEL":           "단수주 소각 — 소각 규모 미미",
  "SHAREHOLDER_SMALL_CANCEL":             "소규모 소각 — 소각 규모 제한적",
  "SHAREHOLDER_BUYBACK_ONLY":             "자사주 취득 — 자기주식 확보",
  "SHAREHOLDER_OPEN_MARKET_BUYBACK":      "자사주 공개매수 — 공개 시장 매수",
  "EARNINGS_LOSS_TO_PROFIT_NO_HISTORY":   "흑자전환 — 당기순이익 기록",
  "EARNINGS_LOSS_TO_PROFIT_1Q":           "1분기 만에 흑자전환 — 분기 기준 이익 전환",
  "EARNINGS_LOSS_TO_PROFIT_3Q":           "3분기 연속 흑자전환 — 분기 기준 이익 유지",
  "EARNINGS_REVENUE_INCREASE":            "매출 증가 — 전기 대비 매출액 상승",
  "EARNINGS_AUDIT_UNQUALIFIED":           "감사의견 적정 — 회계 기준 적합 판정",
  "EARNINGS_OP_PROFIT_IMPROVING":         "영업이익 개선 — 전기 대비 영업이익 증가",
  "MA_MERGER":                            "합병 결정 — 법인 합병 예정",
  "MA_SHAREHOLDER_PROPOSAL":              "주주제안 — 주주 권리 행사",
  "MA_ACTIVIST":                          "행동주의 펀드 등장 — 대주주 지분 취득",
  "MA_BUSINESS_TRANSFER":                 "영업양수도 — 사업 양수 또는 양도",
  "MA_SHARE_EXCHANGE":                    "주식교환/이전 — 지배구조 변경",
  "MA_MAJOR_CHANGE_GENERAL":              "최대주주 변경 — 경영권 변동",
  "MA_BULK_HOLDING_MANAGEMENT":           "대량보유(경영참여 목적) — 5% 초과 지분 보유",
  "MA_PROXY_FIGHT":                       "위임장 대결 — 의결권 위임 경쟁",
  "MA_EGM_DISPUTE":                       "임시주주총회(분쟁) — 임시 주총 소집",
  "MA_OVERSEAS_LISTING":                  "해외증시 상장 추진 — 해외 상장 계획",
  "CAPITAL_RAISING_THIRD_PARTY_CONGLO":   "대기업 계열사 대상 3자배정 — 특정 대상 신주 배정",
  "CAPITAL_RAISING_FREE_INCREASE":        "무상증자 — 주식 수 증가, 액면가 유지",
  "CAPITAL_RAISING_PAID_REDUCTION":       "유상감자 — 주식 수 감소",
  "CAPITAL_RAISING_CB_EARLY_REDEEM":      "CB 조기 상환/만기전 취득 — 사채 조기 상환",
  "CAPITAL_RAISING_CB_PRICE_UP":          "CB 전환가액 상향 조정 — 전환 조건 상향 변경",
  "CAPITAL_RAISING_CB_FACILITY":          "CB 발행(시설자금) — 시설 투자 목적 자금 조달",
  "MA_MAJOR_CHANGE_CONGLO_FIRST":         "대기업 계열사로 최대주주 변경 — 대기업 계열 편입",
};

type Signal = { icon: string; label: string; color: string; bg: string; horizon?: string };

const _NEGATIVE_RULES = new Set([
  "MA_MANAGEMENT_DISPUTE",
  "MA_MAJOR_CHANGE_NEWLY_FORMED",
  "MA_BLOCK_TRADE",
  "BIOTECH_CLINICAL_HOLD",
  "BIOTECH_TECH_RETURN",
  "CAPITAL_RAISING_FREE_REDUCTION",
  "BUSINESS_CONTRACT_TERMINATED",
  "BUSINESS_CONTRACT_MODIFIED",
  "EARNINGS_PROFIT_TO_LOSS_NO_HISTORY",
  "EARNINGS_REVENUE_DECREASE",
  "EARNINGS_LOSS_CONTINUED",
  "SHAREHOLDER_DISPOSAL_OPERATING",
  "SHAREHOLDER_DISPOSAL_STOCK_OPTION",
  "MA_SPLIT_WITH_LISTING",
  "CAPITAL_RAISING_CB_WORKING",
  "CAPITAL_RAISING_DELAYED_PAYMENT",
  "CAPITAL_RAISING_CB_REFIXING",
  "CAPITAL_RAISING_WITHDRAWN",
  "CAPITAL_RAISING_CB_CONVERTED",
  "CAPITAL_RAISING_WARRANT_EXERCISED",
  "SHAREHOLDER_TREASURY_COLLATERAL",
  "SHAREHOLDER_MAJOR_PLEDGE",
  "SHAREHOLDER_STOCK_DIVIDEND",
  "MA_DEBT_TO_EQUITY",
  "MA_DEBT_FORGIVENESS",
  "EARNINGS_LOSS_TO_PROFIT_NON_OP",
  "EARNINGS_OP_PROFIT_WORSENING",
  "RISK_GOING_CONCERN",
  "RISK_CAPITAL_IMPAIRMENT",
  "RISK_MANAGEMENT_ISSUE",
  "RISK_LISTING_REVIEW",
  "BUSINESS_CONTRACT_NA_PCT",
]);

const _POSITIVE_RULES = new Set([
  "BIOTECH_FDA_APPROVAL",
  "BIOTECH_TECH_TRANSFER_AMOUNT",
  "BIOTECH_PHASE3_NDA",
  "SHAREHOLDER_FIRST_BUYBACK_CANCEL",
  "SHAREHOLDER_REPEAT_BUYBACK_CANCEL",
  "SHAREHOLDER_BUYBACK_ONLY",
  "SHAREHOLDER_OPEN_MARKET_BUYBACK",
  "EARNINGS_LOSS_TO_PROFIT_NO_HISTORY",
  "EARNINGS_LOSS_TO_PROFIT_1Q",
  "EARNINGS_LOSS_TO_PROFIT_3Q",
  "EARNINGS_REVENUE_INCREASE",
  "EARNINGS_AUDIT_UNQUALIFIED",
  "EARNINGS_OP_PROFIT_IMPROVING",
  "MA_MERGER",
  "MA_SHAREHOLDER_PROPOSAL",
  "MA_ACTIVIST",
  "MA_BUSINESS_TRANSFER",
  "MA_SHARE_EXCHANGE",
  "MA_MAJOR_CHANGE_GENERAL",
  "MA_BULK_HOLDING_MANAGEMENT",
  "MA_PROXY_FIGHT",
  "MA_EGM_DISPUTE",
  "MA_OVERSEAS_LISTING",
  "CAPITAL_RAISING_THIRD_PARTY_CONGLO",
  "CAPITAL_RAISING_FREE_INCREASE",
  "CAPITAL_RAISING_PAID_REDUCTION",
  "CAPITAL_RAISING_CB_EARLY_REDEEM",
  "CAPITAL_RAISING_CB_PRICE_UP",
  "CAPITAL_RAISING_CB_FACILITY",
  "MA_MAJOR_CHANGE_CONGLO_FIRST",
]);

export type DisclosureNature = "positive" | "negative" | "neutral" | "beneficial" | "adverse";

function _normalizeNature(val: string): DisclosureNature {
  if (val === "beneficial" || val === "positive") return "positive";
  if (val === "adverse" || val === "negative") return "negative";
  return "neutral";
}

export function getNature(item: DisclosureItem): DisclosureNature {
  const sid = item.sub_rule_id || "";
  if (_NEGATIVE_RULES.has(sid)) return "negative";
  if (_POSITIVE_RULES.has(sid)) return "positive";
  if (item.risk_flag != null && item.risk_flag !== "CLEAN") return "negative";
  if (item.category === "DELISTING_RISK") return "negative";

  if (item.cerebras_sentiment) {
    return _normalizeNature(item.cerebras_sentiment);
  }

  if (item.category === "ADMINISTRATIVE") return "neutral";

  if (item.category === "BUSINESS_CONTRACT" && (item.dvi_score ?? 0) >= 50)
    return "positive";

  const s = item.dvi_score ?? 0;
  if (s >= 90) return "positive";
  if (s >= 30) return "neutral";
  return "negative";
}

function getSignal(item: DisclosureItem): Signal {
  const isTrap = item.risk_flag != null && item.risk_flag !== "CLEAN";
  const s = item.dvi_score ?? 0;
  const nature = getNature(item);
  const horizon = item.signal_horizon || "";
  const cat = item.category || "";
  const catLabel = CATEGORY_SIGNAL_LABELS[cat] || "";

  if (item.category === "ADMINISTRATIVE")
    return { icon: "⚪", label: "행정 공시", color: "text-gray-400", bg: "bg-gray-800/40" };

  if (isTrap || s === 0)
    return { icon: "🔴", label: "위험", color: "text-red-400", bg: "bg-red-900/20" };

  if (nature === "positive" && s >= 90) {
    const label = catLabel || "긍정";
    return { icon: "🟢", label, color: "text-green-400", bg: "bg-green-900/20", horizon };
  }

  if (nature === "positive" && s >= 70) {
    const label = catLabel || "긍정";
    return { icon: "🟡", label, color: "text-yellow-400", bg: "bg-yellow-900/20", horizon };
  }

  if (nature === "negative") {
    const label = catLabel || "부정";
    return { icon: "🔴", label, color: "text-red-400", bg: "bg-red-900/20", horizon };
  }

  if (s >= 30)
    return { icon: "⚪", label: catLabel || "중립", color: "text-gray-400", bg: "bg-gray-800/40" };

  return { icon: "🟠", label: catLabel || "주의", color: "text-orange-400", bg: "bg-orange-900/20" };
}

function getSignalDescription(item: DisclosureItem): string | null {
  if (item.risk_flag != null && item.risk_flag !== "CLEAN") return null;
  if (item.category === "ADMINISTRATIVE") return null;
  const sid = item.sub_rule_id || "";
  return SUB_RULE_DESC[sid] || null;
}

// ─── Score badge ──────────────────────────────────────────────

function ScoreBadge({ score }: { score: number | null }) {
  if (score === null || score === undefined) return null;
  let barColor: string;
  let textColor: string;
  if (score >= 90)      { barColor = "bg-green-500";  textColor = "text-green-400"; }
  else if (score >= 70) { barColor = "bg-lime-500";   textColor = "text-lime-400"; }
  else if (score >= 40) { barColor = "bg-yellow-500"; textColor = "text-yellow-400"; }
  else if (score > 0)   { barColor = "bg-orange-500"; textColor = "text-orange-300"; }
  else                  { barColor = "bg-red-500";    textColor = "text-red-400"; }

  return (
    <div className="flex flex-col items-center gap-0.5">
      <div className="text-[9px] font-mono font-bold tracking-tight text-[var(--text-muted)] leading-tight text-center">정보량<br />지수</div>
      <div className={`text-xl font-bold font-mono leading-none ${textColor}`}>{score}</div>
      <div className="w-full h-1 rounded-full bg-[var(--bg-primary)] overflow-hidden mt-0.5">
        <div className={`h-full rounded-full transition-all ${barColor}`} style={{ width: `${score}%` }} />
      </div>
    </div>
  );
}

// ─── Metric card ──────────────────────────────────────────────

function MetricCard({ label, value, status }: { label: string; value: string; status: string }) {
  const borderColor =
    status === "POSITIVE" ? "border-green-500/30" :
    status === "NEGATIVE" ? "border-red-500/30" :
    "border-[var(--border-color)]";
  const valueColor =
    status === "POSITIVE" ? "text-green-400" :
    status === "NEGATIVE" ? "text-red-400" :
    "text-white";

  return (
    <div className={`bg-[var(--bg-primary)] border ${borderColor} rounded-lg px-3 py-2 min-w-0`}>
      <div className="text-[10px] text-[var(--text-muted)] font-medium tracking-wider truncate">{label}</div>
      <div className={`text-sm font-semibold mt-0.5 truncate ${valueColor}`}>{value}</div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────

export default function DisclosureCard({ item, isAdmin = false }: DisclosureCardProps) {
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);
  const cat = item.category ? categoryChip[item.category] : null;
  const signal = getSignal(item);
  const cleanTitle = item.title?.replace(/\s+/g, " ").trim() || "";
  const formattedTime = new Date(item.published_at).toLocaleString("ko-KR", {
    month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit",
  });
  const isPending = item.llm_status === "PENDING" && !item.llm_summary;
  const isTrap = item.risk_flag != null && item.risk_flag !== "CLEAN";
  const isAdministrative = item.category === "ADMINISTRATIVE";
  const relatedStatus = item.related_status || "NONE";

  const handleAnalyze = async () => {
    if (!item.id) return;
    setAnalyzing(true);
    setAnalyzeError(null);
    try {
      await disclosures.analyze(item.id);
      window.location.reload();
    } catch (e) {
      console.error("LLM analysis failed:", e);
      setAnalyzeError("LLM 분석에 실패했습니다");
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="card p-4 animate-in hover:border-[var(--text-muted)] transition-all duration-200">
      {/* ── Row 1: Header ────────────────────────────────── */}
      <div className="flex items-start gap-3">
        {/* Left: ticker + company + category + time */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-xs font-bold text-[var(--accent-blue)] tracking-tight">
              [{item.ticker}]
            </span>
            <span className="text-sm font-semibold text-white truncate">{item.company_name}</span>
            {cat && (
              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${cat.color}`}>
                {cat.label}
              </span>
            )}
            <span className="flex items-center gap-1 text-[10px] text-[var(--text-muted)] ml-auto whitespace-nowrap">
              <Clock size={10} />
              {formattedTime}
            </span>
          </div>
          <h3 className="text-sm font-medium text-[var(--text-secondary)] mt-1 leading-snug line-clamp-2">
            {cleanTitle}
          </h3>
        </div>

        {/* Right: DVI Score */}
        <div className="shrink-0 w-16 pt-1">
          <ScoreBadge score={item.dvi_score} />
        </div>
      </div>

      {/* ── Row 2: Signal Badge ──────────────────────────── */}
      <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold mt-3 ${signal.bg} ${signal.color}`}>
        <span>{signal.icon}</span>
        <span>{signal.label}</span>
        {item.sub_type && !isAdministrative && !isTrap && (
          <span className="text-[var(--text-muted)] font-normal">· {item.sub_type}</span>
        )}
      </div>

      {/* ── Row 2b: Signal Description ───────────────────── */}
      {(() => {
        const desc = getSignalDescription(item);
        return desc ? (
          <div className="mt-1.5 text-xs text-[var(--text-muted)] leading-relaxed">
            <span className="font-medium">{signal.icon === "🟢" || signal.icon === "🟡" ? "✓" : "!"}</span> {desc}
          </div>
        ) : null;
      })()}

      {/* ── Row 3: AI Summary ────────────────────────────── */}
      <div className="mt-3">
        {isAdministrative ? (
          <p className="text-xs text-[var(--text-muted)] italic">행정성 공시 (분석 생략)</p>
        ) : isTrap ? (
          <p className="text-xs text-red-400/70 italic">위험 공시 — FAST-FAIL 매칭 (LLM 분석 생략)</p>
        ) : isPending ? (
          <div className="space-y-1.5">
            <div className="shimmer h-3 w-full rounded" />
            <div className="shimmer h-3 w-3/4 rounded" />
          </div>
        ) : item.llm_summary ? (
          <div className="bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-lg p-3">
            <div className="flex items-center gap-1.5 mb-1.5">
              <span className="text-xs">📋</span>
              <span className="text-[10px] font-bold text-[var(--text-muted)] tracking-wider uppercase">AI 핵심 요약</span>
            </div>
            <p className="text-sm text-[var(--text-secondary)] leading-relaxed whitespace-pre-wrap">
              {item.llm_summary}
            </p>
          </div>
        ) : (
          <p className="text-xs text-[var(--text-muted)]">
            점수 {item.dvi_score} — 60점 이상만 AI 요약 제공
          </p>
        )}
      </div>

      {/* ── Row 3b: Related Disclosure Analysis ──────────── */}
      {relatedStatus === "ANALYZING" && (
        <div className="mt-2 bg-blue-900/10 border border-blue-500/20 rounded-lg p-3">
          <div className="flex items-center gap-1.5 mb-1.5">
            <span className="text-xs">⚡</span>
            <span className="text-[10px] font-bold text-blue-400 tracking-wider uppercase">관련공시 분석중입니다...</span>
          </div>
          <div className="space-y-1.5">
            <div className="shimmer h-3 w-full rounded" />
            <div className="shimmer h-3 w-2/3 rounded" />
          </div>
        </div>
      )}
      {relatedStatus === "MERGED" && item.merged_summary && (
        <div className="mt-2 bg-[var(--bg-primary)] border border-blue-500/30 rounded-lg p-3">
          <div className="flex items-center gap-1.5 mb-1.5">
            <span className="text-xs">📋</span>
            <span className="text-[10px] font-bold text-blue-400 tracking-wider uppercase">관련공시 포함 통합 분석</span>
            {item.merged_sentiment === "BENEFICIAL" && <span className="text-[10px] text-green-400">· 긍정</span>}
            {item.merged_sentiment === "ADVERSE" && <span className="text-[10px] text-red-400">· 부정</span>}
            {item.merged_horizon === "LONG_TERM" && <span className="text-[10px] text-[var(--text-muted)]">· 장기</span>}
            {item.merged_horizon === "SHORT_TERM" && <span className="text-[10px] text-[var(--text-muted)]">· 단기</span>}
            {item.merged_confidence && <span className="text-[10px] text-[var(--text-muted)]">· 신뢰도 {item.merged_confidence}</span>}
          </div>
          <p className="text-sm text-[var(--text-secondary)] leading-relaxed whitespace-pre-wrap">
            {item.merged_summary}
          </p>
        </div>
      )}

      {/* ── Row 3c: Cerebras Insight (ambiguous disclosures) ── */}
      {item.cerebras_sentiment && item.cerebras_reason && (
        <div className="mt-2 bg-purple-900/10 border border-purple-500/20 rounded-lg p-3">
          <div className="flex items-center gap-1.5 mb-1.5">
            <span className="text-[10px] font-bold text-purple-400 tracking-wider uppercase">🤖 AI 모호 공시 분석</span>
            {item.cerebras_confidence && (
              <span className="text-[10px] text-purple-400/60">· 신뢰도 {item.cerebras_confidence}</span>
            )}
          </div>
          <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
            {item.cerebras_reason}
          </p>
        </div>
      )}

      {/* ── Row 4: Key Metrics Grid ──────────────────────── */}
      {item.key_metrics && item.key_metrics.length > 0 && !isAdministrative && (
        <div className="mt-3 grid grid-cols-2 sm:grid-cols-3 gap-2">
          {item.key_metrics.map((m, i) => (
            <MetricCard key={i} label={m.label} value={m.value} status={m.status} />
          ))}
        </div>
      )}

      {/* ── Error toast ──────────────────────────────────── */}
      {analyzeError && (
        <div className="mt-2 bg-red-900/20 border border-red-500/30 rounded-lg px-3 py-2 text-xs text-red-400 flex items-center justify-between">
          <span>{analyzeError}</span>
          <button onClick={() => setAnalyzeError(null)} className="text-red-400/60 hover:text-red-300 ml-2">✕</button>
        </div>
      )}

      {/* ── Row 5: Footer ────────────────────────────────── */}
      <div className="flex items-center justify-between mt-3 pt-2 border-t border-[var(--border-color)]">
        <div className="flex items-center gap-3">
          <a
            href={item.dart_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-[var(--accent-blue)] hover:text-[var(--accent-mint)] transition-colors"
          >
            <ExternalLink size={11} />
            DART 원문 보기
          </a>
          {isAdmin && !isAdministrative && !isTrap && (!item.llm_summary || item.llm_summary.includes("실패")) && (
            <button
              onClick={handleAnalyze}
              disabled={analyzing}
              className="inline-flex items-center gap-1 text-xs text-[var(--accent-mint)] hover:text-white transition-colors disabled:opacity-50"
            >
              <Sparkles size={11} />
              {analyzing ? "분석 중..." : "LLM 분석"}
            </button>
          )}
        </div>
        {!isAdministrative && !isTrap && !isPending && item.dvi_score !== null && item.dvi_score < 60 && (
          <span className="flex items-center gap-1 text-[10px] text-[var(--text-muted)]">
            <Info size={10} />
            AI 요약 미제공
          </span>
        )}
        {!isAdministrative && !isTrap && !isPending && item.llm_summary && (
          <span className="flex items-center gap-1 text-[10px] text-[var(--text-muted)]">
            <Info size={10} />
            AI 분석은 참고용입니다
          </span>
        )}
      </div>
    </div>
  );
}
