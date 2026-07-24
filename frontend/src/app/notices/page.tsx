"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { MessageSquare, Pin, Calendar, ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import { notices_api, type Notice } from "@/lib/api";

export default function NoticesPage() {
  const [notices, setNotices] = useState<Notice[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const perPage = 20;

  useEffect(() => {
    setLoading(true);
    setError(null);
    notices_api
      .list(page, perPage)
      .then((res) => {
        setNotices(res.data);
        setTotal(res.total);
      })
      .catch(() => setError("공지사항을 불러오지 못했습니다"))
      .finally(() => setLoading(false));
  }, [page]);

  const totalPages = Math.ceil(total / perPage);

  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <div className="flex items-center gap-3 mb-8">
        <div className="w-10 h-10 rounded-lg bg-[var(--accent-mint)]/10 flex items-center justify-center">
          <MessageSquare size={20} className="text-[var(--accent-mint)]" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">공지사항</h1>
          <p className="text-xs text-[var(--text-secondary)]">DART0s 업데이트 및 안내</p>
        </div>
      </div>

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="card p-5 animate-pulse">
              <div className="h-4 bg-white/5 rounded w-3/4 mb-3" />
              <div className="h-3 bg-white/5 rounded w-1/3" />
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="card p-8 text-center">
          <p className="text-red-400 text-sm">{error}</p>
          <button onClick={() => setPage(1)} className="btn-outline text-xs mt-4">
            다시 시도
          </button>
        </div>
      ) : notices.length === 0 ? (
        <div className="card p-12 text-center">
          <MessageSquare size={32} className="mx-auto text-[var(--text-muted)] mb-3" />
          <p className="text-[var(--text-secondary)] text-sm">등록된 공지사항이 없습니다</p>
        </div>
      ) : (
        <>
          <div className="space-y-3">
            {notices.map((n) => (
              <Link
                key={n.id}
                href={`/notices/${n.id}`}
                className="card p-5 block hover:border-[var(--accent-mint)]/30 transition-all group"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      {n.pinned && (
                        <span className="flex items-center gap-1 text-[10px] font-semibold text-[var(--accent-mint)] bg-[var(--accent-mint)]/10 px-2 py-0.5 rounded-full">
                          <Pin size={10} />
                          고정
                        </span>
                      )}
                      <h2 className="text-sm font-bold text-white truncate group-hover:text-[var(--accent-mint)] transition-colors">
                        {n.title}
                      </h2>
                    </div>
                    <div className="flex items-center gap-3 text-[11px] text-[var(--text-muted)]">
                      <span className="flex items-center gap-1">
                        <Calendar size={10} />
                        {new Date(n.created_at).toLocaleDateString("ko-KR")}
                      </span>
                      <span>{n.author_email}</span>
                    </div>
                  </div>
                  <ChevronRight size={16} className="text-[var(--text-muted)] shrink-0 mt-1" />
                </div>
              </Link>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-8">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="btn-outline text-xs flex items-center gap-1 disabled:opacity-30"
              >
                <ChevronLeft size={14} /> 이전
              </button>

              {Array.from({
                length: Math.min(totalPages, 5),
              }).map((_, i) => {
                const start = Math.max(1, Math.min(page - 2, totalPages - 4));
                const p = start + i;
                if (p > totalPages) return null;
                return (
                  <button
                    key={p}
                    onClick={() => setPage(p)}
                    className={`w-8 h-8 rounded-lg text-xs font-medium transition-colors ${
                      p === page
                        ? "bg-[var(--accent-mint)] text-black"
                        : "text-[var(--text-secondary)] hover:text-white"
                    }`}
                  >
                    {p}
                  </button>
                );
              })}

              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="btn-outline text-xs flex items-center gap-1 disabled:opacity-30"
              >
                다음 <ChevronRight size={14} />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
