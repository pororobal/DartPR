"use client";

import { Copy, Check } from "lucide-react";
import { useState } from "react";

const codeBlock = (code: string) => {
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative">
      <pre className="bg-[var(--bg-hover)] border border-[var(--border-color)] rounded-lg p-4 overflow-x-auto text-xs font-mono text-[var(--text-secondary)]">
        <code>{code}</code>
      </pre>
      <button onClick={copy} className="absolute top-2 right-2 text-[var(--text-muted)] hover:text-white">
        {copied ? <Check size={14} /> : <Copy size={14} />}
      </button>
    </div>
  );
};

const endpoints = [
  {
    method: "GET",
    path: "/api/v1/dev/disclosures/list",
    auth: "X-API-Key",
    desc: "전체 공시 목록을 조회합니다. Developer 플랜 전용.",
    curl: `curl -H "X-API-Key: your_api_key_here" \\
  https://your-api.com/api/v1/dev/disclosures/list`,
    response: `{
  "data": [
    {
      "dart_rcept_no": "20240723000123",
      "dart_url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20240723000123",
      "ticker": "005930",
      "company_name": "삼성전자",
      "title": "시설자금 조달을 위한 CB 발행 결정",
      "category": "CAPITAL_RAISING",
      "llm_summary": "시설자금 목적이므로 긍정적...",
      "llm_status": "DONE",
      "key_metrics": [...]
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 50
}`,
  },
  {
    method: "GET",
    path: "/api/v1/dev/disclosures/history",
    auth: "X-API-Key",
    desc: "히스토리 조회 (검색/필터/페이지네이션 지원).",
    curl: `curl -H "X-API-Key: your_api_key_here" \\
  "https://your-api.com/api/v1/dev/disclosures/history?ticker=005930&page=1&per_page=20"`,
    response: `{
  "data": [...],
  "total": 142,
  "page": 1,
  "per_page": 20
}`,
  },
];

export default function ApiDocsPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <h1 className="text-2xl font-bold text-white mb-2">API 문서</h1>
      <p className="text-sm text-[var(--text-secondary)] mb-8">
        Developer 플랜 사용자를 위한 자동매매 연동 API입니다.
      </p>

      {/* Authentication */}
      <section className="mb-10">
        <h2 className="text-lg font-bold text-white mb-3">인증</h2>
        <div className="card p-4">
          <p className="text-sm text-[var(--text-secondary)] mb-2">
            모든 Developer API 요청은 <code className="text-[var(--accent-mint)] bg-[var(--bg-hover)] px-1 rounded text-xs font-mono">X-API-Key</code> 헤더에 API Key를 포함해야 합니다.
          </p>
          <p className="text-sm text-[var(--text-secondary)]">
            API Key는 마이페이지에서 확인할 수 있습니다.
          </p>
        </div>
      </section>

      {/* Rate Limit */}
      <section className="mb-10">
        <h2 className="text-lg font-bold text-white mb-3">Rate Limit</h2>
        <div className="card p-4">
          <p className="text-sm text-[var(--text-secondary)]">
            현재 Rate Limit은 적용되지 않았습니다. 양호한 사용을 부탁드립니다.
            추후 분당 100회로 제한될 수 있습니다.
          </p>
        </div>
      </section>

      {/* Endpoints */}
      <section>
        <h2 className="text-lg font-bold text-white mb-3">엔드포인트</h2>
        <div className="space-y-6">
          {endpoints.map((ep, i) => (
            <div key={i} className="card p-5">
              <div className="flex items-center gap-2 mb-3">
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                    ep.method === "GET"
                      ? "bg-green-900/40 text-green-400"
                      : "bg-blue-900/40 text-blue-400"
                  }`}
                >
                  {ep.method}
                </span>
                <code className="text-xs font-mono text-white">{ep.path}</code>
              </div>

              <p className="text-sm text-[var(--text-secondary)] mb-3">{ep.desc}</p>
              <p className="text-[10px] text-[var(--text-muted)] mb-1">Auth: {ep.auth}</p>

              <div className="mb-3">
                <p className="text-[10px] text-[var(--text-muted)] font-bold uppercase tracking-wider mb-1">cURL</p>
                <div className="relative">
                  <pre className="bg-[var(--bg-hover)] border border-[var(--border-color)] rounded-lg p-3 overflow-x-auto text-xs font-mono text-[var(--text-secondary)]">
                    <code>{ep.curl}</code>
                  </pre>
                </div>
              </div>

              <div>
                <p className="text-[10px] text-[var(--text-muted)] font-bold uppercase tracking-wider mb-1">응답 예시</p>
                <pre className="bg-[var(--bg-hover)] border border-[var(--border-color)] rounded-lg p-3 overflow-x-auto text-xs font-mono text-[var(--text-secondary)] max-h-60 overflow-y-auto">
                  <code>{ep.response}</code>
                </pre>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
