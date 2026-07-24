"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { auth } from "@/lib/api";
import { User, ChevronDown, Crown, LogOut, CreditCard, Clock, Zap } from "lucide-react";

const planLabels: Record<string, string> = {
  free: "Free",
  pro: "Pro",
  admin: "Admin",
};

const planColors: Record<string, string> = {
  free: "bg-gray-700 text-gray-300",
  pro: "bg-yellow-900/40 text-yellow-400",
  admin: "bg-red-900/40 text-red-400",
};

function getDaysLeft(expiresAt: string | null | undefined): number | null {
  if (!expiresAt) return null;
  const diff = new Date(expiresAt).getTime() - Date.now();
  return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)));
}

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [session, setSession] = useState<{ user: { email?: string; id?: string } } | null>(null);
  const [plan, setPlan] = useState<string>("free");
  const [planExpiresAt, setPlanExpiresAt] = useState<string | null>(null);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll);

    const loadUser = async () => {
      const { data } = await supabase.auth.getSession();
      if (data.session) {
        setSession(data.session);
        try {
          const userData = await auth.me();
          setPlan(userData.plan || "free");
          setPlanExpiresAt((userData as any).plan_expires_at || null);
        } catch {
          setPlan("free");
        }
      }
    };
    loadUser();

    const { data: listener } = supabase.auth.onAuthStateChange(async (_event, session) => {
      setSession(session);
      if (session) {
        try {
          const userData = await auth.me();
          setPlan(userData.plan || "free");
          setPlanExpiresAt((userData as any).plan_expires_at || null);
        } catch {
          setPlan("free");
        }
      } else {
        setPlan("free");
        setPlanExpiresAt(null);
      }
    });

    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);

    return () => {
      window.removeEventListener("scroll", handleScroll);
      listener?.subscription.unsubscribe();
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    localStorage.removeItem("supabase_access_token");
    setDropdownOpen(false);
    router.push("/");
  };

  const daysLeft = getDaysLeft(planExpiresAt);

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled ? "glass" : "bg-transparent"
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link href="/" className="text-lg md:text-xl font-bold tracking-tight">
            <span className="text-[var(--accent-mint)]">Dart</span>
            <span className="text-white">PR</span>
          </Link>

          <div className="hidden md:flex items-center gap-8">
            <Link
              href="/live"
              className="text-sm font-medium text-[var(--text-secondary)] hover:text-white transition-colors"
            >
              실시간 피드
            </Link>
            <Link
              href="/history"
              className="text-sm font-medium text-[var(--text-secondary)] hover:text-white transition-colors"
            >
              히스토리
            </Link>
            <Link
              href="/intro"
              className="text-sm font-medium text-[var(--text-secondary)] hover:text-white transition-colors"
            >
              소개
            </Link>
            <Link
              href="/notices"
              className="text-sm font-medium text-[var(--text-secondary)] hover:text-white transition-colors"
            >
              공지사항
            </Link>
            <Link
              href="/pricing"
              className="text-sm font-medium text-[var(--text-secondary)] hover:text-white transition-colors"
            >
              플랜
            </Link>

            {session ? (
              <div className="relative" ref={dropdownRef}>
                <button
                  onClick={() => setDropdownOpen(!dropdownOpen)}
                  className="flex items-center gap-2 text-sm text-[var(--text-secondary)] hover:text-white transition-colors px-3 py-1.5 rounded-lg hover:bg-white/5"
                >
                  <User size={16} />
                  <span>{session.user?.email?.split("@")[0]}</span>
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${planColors[plan] || planColors.free}`}>
                    {planLabels[plan] || "Free"}
                  </span>
                  <ChevronDown size={14} className={`transition-transform ${dropdownOpen ? "rotate-180" : ""}`} />
                </button>

                {dropdownOpen && (
                  <div className="absolute right-0 top-full mt-2 w-64 glass border border-[var(--border-color)] rounded-xl shadow-2xl overflow-hidden">
                    <div className="p-4 border-b border-[var(--border-color)]">
                      <p className="text-sm font-medium text-white truncate">{session.user?.email}</p>
                      <div className="flex items-center gap-1.5 mt-2">
                        <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${planColors[plan] || planColors.free}`}>
                          {planLabels[plan] || "Free"}
                        </span>
                        {plan !== "free" && daysLeft !== null && (
                          <span className="text-xs text-[var(--text-muted)] flex items-center gap-1">
                            <Clock size={10} />
                            잔여 {daysLeft}일
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="p-2">
                      {plan === "free" ? (
                        <Link
                          href="/pricing"
                          onClick={() => setDropdownOpen(false)}
                          className="flex items-center gap-2 w-full px-3 py-2 text-sm text-[var(--text-secondary)] hover:text-white hover:bg-white/5 rounded-lg transition-colors"
                        >
                          <Crown size={14} className="text-yellow-400" />
                          플랜 업그레이드
                        </Link>
                      ) : (
                        <Link
                          href="/pricing"
                          onClick={() => setDropdownOpen(false)}
                          className="flex items-center gap-2 w-full px-3 py-2 text-sm text-[var(--text-secondary)] hover:text-white hover:bg-white/5 rounded-lg transition-colors"
                        >
                          <CreditCard size={14} />
                          플랜 관리
                        </Link>
                      )}
                      <button
                        onClick={handleLogout}
                        className="flex items-center gap-2 w-full px-3 py-2 text-sm text-red-400 hover:text-red-300 hover:bg-red-900/10 rounded-lg transition-colors"
                      >
                        <LogOut size={14} />
                        로그아웃
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link href="/login" className="btn-outline text-sm py-1.5 px-3">
                  로그인
                </Link>
                <Link href="/signup" className="btn-primary text-sm py-1.5 px-3">
                  회원가입
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
