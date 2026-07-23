"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { UserCircle, Copy, Check, LogOut } from "lucide-react";

export default function MyPage() {
  const [user, setUser] = useState<{ email: string; plan: string; api_key?: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const fetchUser = async () => {
      const { data } = await supabase.auth.getSession();
      if (!data.session) {
        router.push("/login");
        return;
      }

      try {
        const res = await fetch("/api/v1/auth/me", {
          headers: { Authorization: `Bearer ${data.session.access_token}` },
        });
        if (res.ok) {
          setUser(await res.json());
        }
      } catch {
        // fallback
      }
      setLoading(false);
    };

    fetchUser();
  }, [router]);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    localStorage.removeItem("supabase_access_token");
    router.push("/");
  };

  const handleCopyKey = () => {
    if (user?.api_key) {
      navigator.clipboard.writeText(user.api_key);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (loading) {
    return (
      <div className="max-w-lg mx-auto px-4 py-12">
        <div className="card p-6">
          <div className="shimmer h-6 w-32 mb-4" />
          <div className="shimmer h-4 w-48 mb-2" />
          <div className="shimmer h-4 w-24" />
        </div>
      </div>
    );
  }

  if (!user) return null;

  const planColors: Record<string, string> = {
    free: "text-[var(--text-muted)]",
    pro: "text-[var(--accent-mint)]",
    developer: "text-[var(--accent-blue)]",
  };

  return (
    <div className="max-w-lg mx-auto px-4 py-12">
      <h1 className="text-xl font-bold text-white mb-6">마이페이지</h1>

      <div className="card p-6 space-y-6">
        {/* Account info */}
        <div className="flex items-center gap-3">
          <UserCircle size={40} className="text-[var(--text-muted)]" />
          <div>
            <p className="text-sm font-medium text-white">{user.email}</p>
            <p className={`text-xs font-bold ${planColors[user.plan] || "text-[var(--text-muted)]"}`}>
              {user.plan === "free" ? "Free" : user.plan === "pro" ? "Pro" : "Developer"} 플랜
            </p>
          </div>
        </div>

        {/* Developer API Key */}
        {user.plan === "developer" && user.api_key && (
          <div>
            <label className="text-xs text-[var(--text-secondary)] font-bold uppercase tracking-wider">
              API Key
            </label>
            <div className="flex items-center gap-2 mt-1">
              <code className="flex-1 bg-[var(--bg-hover)] border border-[var(--border-color)] rounded px-3 py-2 text-xs font-mono text-[var(--accent-mint)] truncate">
                {user.api_key}
              </code>
              <button
                onClick={handleCopyKey}
                className="btn-outline text-xs py-2 px-3 flex-shrink-0"
              >
                {copied ? <Check size={14} className="text-[var(--accent-mint)]" /> : <Copy size={14} />}
              </button>
            </div>
          </div>
        )}

        {/* Logout */}
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 text-xs text-[var(--text-muted)] hover:text-[var(--accent-red)] transition-colors"
        >
          <LogOut size={14} />
          로그아웃
        </button>
      </div>
    </div>
  );
}
