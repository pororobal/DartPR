"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  MessageSquare, Pin, Calendar, ArrowLeft, Loader2, Clock, User
} from "lucide-react";
import { notices_api, type Notice } from "@/lib/api";

export default function NoticeDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [notice, setNotice] = useState<Notice | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setError(null);
    notices_api
      .get(id)
      .then(setNotice)
      .catch(() => setError("공지사항을 불러오지 못했습니다"))
      .finally(() => setLoading(false));
  }, [id]);

  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <button
        onClick={() => router.push("/notices")}
        className="flex items-center gap-1.5 text-xs text-[var(--text-secondary)] hover:text-white transition-colors mb-6"
      >
        <ArrowLeft size={14} />
        공지사항 목록
      </button>

      {loading ? (
        <div className="card p-8 animate-pulse">
          <div className="h-5 bg-white/5 rounded w-1/4 mb-4" />
          <div className="h-7 bg-white/5 rounded w-3/4 mb-4" />
          <div className="h-3 bg-white/5 rounded w-1/3 mb-8" />
          <div className="space-y-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-3 bg-white/5 rounded w-full" />
            ))}
          </div>
        </div>
      ) : error ? (
        <div className="card p-8 text-center">
          <p className="text-red-400 text-sm">{error}</p>
          <button
            onClick={() => router.push("/notices")}
            className="btn-outline text-xs mt-4"
          >
            목록으로
          </button>
        </div>
      ) : !notice ? (
        <div className="card p-12 text-center">
          <MessageSquare size={32} className="mx-auto text-[var(--text-muted)] mb-3" />
          <p className="text-[var(--text-secondary)] text-sm">존재하지 않는 공지사항입니다</p>
          <button
            onClick={() => router.push("/notices")}
            className="btn-outline text-xs mt-4"
          >
            목록으로
          </button>
        </div>
      ) : (
        <article className="card p-8">
          <div className="flex items-center gap-2 mb-4">
            {notice.pinned && (
              <span className="flex items-center gap-1 text-[10px] font-semibold text-[var(--accent-mint)] bg-[var(--accent-mint)]/10 px-2 py-0.5 rounded-full">
                <Pin size={10} />
                고정
              </span>
            )}
          </div>

          <h1 className="text-xl md:text-2xl font-bold text-white mb-4">
            {notice.title}
          </h1>

          <div className="flex items-center gap-4 text-[11px] text-[var(--text-muted)] mb-8 pb-6 border-b border-[var(--border-color)]">
            <span className="flex items-center gap-1">
              <User size={12} />
              {notice.author_email}
            </span>
            <span className="flex items-center gap-1">
              <Calendar size={12} />
              {new Date(notice.created_at).toLocaleDateString("ko-KR", {
                year: "numeric",
                month: "long",
                day: "numeric",
              })}
            </span>
            {notice.updated_at && (
              <span className="flex items-center gap-1">
                <Clock size={12} />
                수정됨
              </span>
            )}
          </div>

          <div className="text-sm text-[var(--text-secondary)] leading-relaxed whitespace-pre-wrap">
            {notice.content}
          </div>
        </article>
      )}
    </div>
  );
}
