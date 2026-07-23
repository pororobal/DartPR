"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { supabase } from "@/lib/supabase";
import { auth } from "@/lib/api";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const { data, error: loginError } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (loginError) throw loginError;
      if (!data.session) throw new Error("No session returned");

      localStorage.setItem("supabase_access_token", data.session.access_token);

      // Sync to our backend (non-critical if fails)
      try {
        await auth.login(email, password);
      } catch {
        // non-fatal
      }

      router.push("/live");
    } catch (e) {
      setError(e instanceof Error ? e.message : "로그인 실패");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[70vh] flex items-center justify-center px-4">
      <div className="card p-8 w-full max-w-sm">
        <h1 className="text-xl font-bold text-white text-center mb-6">로그인</h1>

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="text-xs text-[var(--text-secondary)]">이메일</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="email@example.com"
              className="w-full mt-1 bg-[var(--bg-hover)] border border-[var(--border-color)] rounded px-3 py-2 text-sm text-white placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-mint)]"
            />
          </div>
          <div>
            <label className="text-xs text-[var(--text-secondary)]">비밀번호</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="••••••"
              className="w-full mt-1 bg-[var(--bg-hover)] border border-[var(--border-color)] rounded px-3 py-2 text-sm text-white placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-mint)]"
            />
          </div>

          {error && (
            <p className="text-xs text-[var(--accent-red)]">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full text-sm disabled:opacity-50"
          >
            {loading ? "처리 중..." : "로그인"}
          </button>
        </form>

        <p className="text-xs text-[var(--text-secondary)] text-center mt-4">
          계정이 없으신가요?{" "}
          <Link href="/signup" className="text-[var(--accent-mint)] hover:underline">
            회원가입
          </Link>
        </p>
      </div>
    </div>
  );
}
