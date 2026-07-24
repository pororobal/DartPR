"use client";

import { useEffect, useState } from "react";
import { notices_api, auth, type Notice } from "@/lib/api";
import {
  MessageSquare, Pin, Plus, Trash2, Edit3, X, Loader2,
  Calendar, Check, AlertCircle
} from "lucide-react";

type FormState = "idle" | "create" | "edit";

export default function AdminNoticesPage() {
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);
  const [notices, setNotices] = useState<Notice[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // form
  const [formState, setFormState] = useState<FormState>("idle");
  const [editId, setEditId] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [pinned, setPinned] = useState(false);
  const [saving, setSaving] = useState(false);

  // confirm delete
  const [deleteId, setDeleteId] = useState<string | null>(null);

  useEffect(() => {
    auth.me()
      .then((u) => {
        if (u.plan !== "admin") {
          setIsAdmin(false);
          return;
        }
        setIsAdmin(true);
        loadNotices();
      })
      .catch(() => setIsAdmin(false));
  }, []);

  function loadNotices() {
    setLoading(true);
    setError(null);
    notices_api
      .list(1, 100)
      .then((res) => {
        setNotices(res.data);
        setTotal(res.total);
      })
      .catch(() => setError("공지사항을 불러오지 못했습니다"))
      .finally(() => setLoading(false));
  }

  function resetForm() {
    setTitle("");
    setContent("");
    setPinned(false);
    setEditId(null);
    setFormState("idle");
  }

  function handleEdit(n: Notice) {
    setTitle(n.title);
    setContent(n.content);
    setPinned(n.pinned);
    setEditId(n.id);
    setFormState("edit");
  }

  function handleSave() {
    if (!title.trim() || !content.trim()) return;
    setSaving(true);
    const promise =
      formState === "edit" && editId
        ? notices_api.update(editId, { title: title.trim(), content: content.trim(), pinned })
        : notices_api.create(title.trim(), content.trim(), pinned);

    promise
      .then(() => {
        resetForm();
        loadNotices();
      })
      .catch(() => setError("저장에 실패했습니다"))
      .finally(() => setSaving(false));
  }

  function handleDelete(id: string) {
    setSaving(true);
    notices_api
      .delete(id)
      .then(() => {
        setDeleteId(null);
        loadNotices();
      })
      .catch(() => setError("삭제에 실패했습니다"))
      .finally(() => setSaving(false));
  }

  if (isAdmin === null) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12 flex items-center justify-center">
        <Loader2 size={24} className="animate-spin text-[var(--accent-mint)]" />
      </div>
    );
  }

  if (isAdmin === false) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12 text-center">
        <AlertCircle size={40} className="mx-auto text-red-400 mb-4" />
        <h1 className="text-xl font-bold text-white mb-2">접근 권한이 없습니다</h1>
        <p className="text-sm text-[var(--text-secondary)]">관리자만 접근할 수 있는 페이지입니다.</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-[var(--accent-mint)]/10 flex items-center justify-center">
            <MessageSquare size={20} className="text-[var(--accent-mint)]" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">공지사항 관리</h1>
            <p className="text-xs text-[var(--text-secondary)]">총 {total}개</p>
          </div>
        </div>
        {formState === "idle" && (
          <button
            onClick={() => setFormState("create")}
            className="btn-primary text-xs flex items-center gap-1.5"
          >
            <Plus size={14} />
            새 공지사항
          </button>
        )}
      </div>

      {error && (
        <div className="flex items-center gap-2 text-xs text-red-400 bg-red-900/10 border border-red-900/30 rounded-lg px-4 py-2 mb-6">
          <AlertCircle size={14} />
          {error}
        </div>
      )}

      {/* Form */}
      {formState !== "idle" && (
        <div className="card p-6 mb-8 border border-[var(--accent-mint)]/20">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-bold text-white">
              {formState === "create" ? "새 공지사항 작성" : "공지사항 수정"}
            </h2>
            <button onClick={resetForm} className="text-[var(--text-muted)] hover:text-white transition-colors">
              <X size={16} />
            </button>
          </div>

          <div className="space-y-4">
            <input
              type="text"
              placeholder="제목"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-lg px-4 py-2.5 text-sm text-white placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-mint)]/50 transition-colors"
            />
            <textarea
              placeholder="내용"
              rows={8}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className="w-full bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-lg px-4 py-2.5 text-sm text-white placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-mint)]/50 transition-colors resize-y"
            />
            <label className="flex items-center gap-2 text-xs text-[var(--text-secondary)] cursor-pointer">
              <input
                type="checkbox"
                checked={pinned}
                onChange={(e) => setPinned(e.target.checked)}
                className="accent-[var(--accent-mint)]"
              />
              <Pin size={12} />
              상단 고정
            </label>
            <div className="flex items-center gap-2 justify-end">
              <button onClick={resetForm} className="btn-outline text-xs">
                취소
              </button>
              <button
                onClick={handleSave}
                disabled={!title.trim() || !content.trim() || saving}
                className="btn-primary text-xs flex items-center gap-1.5 disabled:opacity-40"
              >
                {saving ? <Loader2 size={12} className="animate-spin" /> : <Check size={12} />}
                {saving ? "저장 중..." : "저장"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* List */}
      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="card p-5 animate-pulse">
              <div className="h-4 bg-white/5 rounded w-3/4 mb-3" />
              <div className="h-3 bg-white/5 rounded w-1/3" />
            </div>
          ))}
        </div>
      ) : notices.length === 0 ? (
        <div className="card p-12 text-center">
          <MessageSquare size={32} className="mx-auto text-[var(--text-muted)] mb-3" />
          <p className="text-[var(--text-secondary)] text-sm">등록된 공지사항이 없습니다</p>
        </div>
      ) : (
        <div className="space-y-2">
          {notices.map((n) => (
            <div
              key={n.id}
              className="card p-4 flex items-center justify-between gap-4"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-0.5">
                  {n.pinned && (
                    <Pin size={10} className="text-[var(--accent-mint)] shrink-0" />
                  )}
                  <span className="text-sm font-medium text-white truncate">{n.title}</span>
                </div>
                <div className="flex items-center gap-3 text-[11px] text-[var(--text-muted)]">
                  <span className="flex items-center gap-1">
                    <Calendar size={10} />
                    {new Date(n.created_at).toLocaleDateString("ko-KR")}
                  </span>
                  <span>{n.author_email}</span>
                </div>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <button
                  onClick={() => handleEdit(n)}
                  className="w-8 h-8 rounded-lg flex items-center justify-center text-[var(--text-muted)] hover:text-white hover:bg-white/5 transition-colors"
                >
                  <Edit3 size={14} />
                </button>
                <button
                  onClick={() => setDeleteId(n.id)}
                  className="w-8 h-8 rounded-lg flex items-center justify-center text-red-400 hover:bg-red-900/20 transition-colors"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Delete confirm */}
      {deleteId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="card p-6 max-w-sm mx-4 text-center">
            <AlertCircle size={32} className="mx-auto text-red-400 mb-3" />
            <p className="text-sm text-white font-bold mb-1">공지사항 삭제</p>
            <p className="text-xs text-[var(--text-secondary)] mb-6">정말 삭제하시겠습니까? 되돌릴 수 없습니다.</p>
            <div className="flex items-center justify-center gap-2">
              <button onClick={() => setDeleteId(null)} className="btn-outline text-xs">
                취소
              </button>
              <button
                onClick={() => handleDelete(deleteId)}
                disabled={saving}
                className="bg-red-500 text-white text-xs font-semibold px-4 py-2 rounded-lg hover:bg-red-600 transition-colors disabled:opacity-40 flex items-center gap-1.5"
              >
                {saving ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
                삭제
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
