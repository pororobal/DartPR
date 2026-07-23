"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { User } from "lucide-react";

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [session, setSession] = useState<{ user: { email?: string } } | null>(null);
  const router = useRouter();

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll);

    supabase.auth.getSession().then(({ data }) => {
      if (data.session) setSession(data.session);
    });

    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });

    return () => {
      window.removeEventListener("scroll", handleScroll);
      listener?.subscription.unsubscribe();
    };
  }, []);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    localStorage.removeItem("supabase_access_token");
    router.push("/");
  };

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled ? "glass" : "bg-transparent"
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link href="/" className="text-xl font-bold tracking-tight">
            <span className="text-[var(--accent-mint)]">DART</span>
            <span className="text-white">0s</span>
          </Link>

          <div className="hidden md:flex items-center gap-6">
            <Link href="/live" className="text-sm text-[var(--text-secondary)] hover:text-white transition-colors">
              실시간 피드
            </Link>
            <Link href="/history" className="text-sm text-[var(--text-secondary)] hover:text-white transition-colors">
              히스토리
            </Link>
            <Link href="/pricing" className="text-sm text-[var(--text-secondary)] hover:text-white transition-colors">
              플랜
            </Link>

            {session ? (
              <div className="flex items-center gap-3">
                <Link
                  href="/mypage"
                  className="flex items-center gap-1.5 text-sm text-[var(--text-secondary)] hover:text-white transition-colors"
                >
                  <User size={16} />
                  <span>{session.user?.email?.split("@")[0]}</span>
                </Link>
                <button onClick={handleLogout} className="btn-outline text-xs py-1.5 px-3">
                  로그아웃
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link href="/login" className="btn-outline text-xs py-1.5 px-3">
                  로그인
                </Link>
                <Link href="/signup" className="btn-primary text-xs py-1.5 px-3">
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
