"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { supabase } from "@/lib/supabase";
import { disclosures, DisclosureItem, auth } from "@/lib/api";
import DisclosureCard, { getNature, DisclosureNature } from "@/components/DisclosureCard";
import { RefreshCw, AlertCircle, Lock, Crown, TrendingUp, TrendingDown } from "lucide-react";

type FilterMode = "all" | "positive" | "negative";

const FILTER_OPTIONS: { key: FilterMode; label: string; icon: any }[] = [
  { key: "all", label: "전체", icon: null },
  { key: "positive", label: "호재", icon: TrendingUp },
  { key: "negative", label: "악재", icon: TrendingDown },
];

export default function LivePage() {
  const [items, setItems] = useState<DisclosureItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<any>(null);
  const [isPremium, setIsPremium] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [filter, setFilter] = useState<FilterMode>("all");

  // Check auth state + plan from backend API
  useEffect(() => {
    const checkAuth = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      setUser(session?.user || null);
      if (session) {
        try {
          const userData = await auth.me();
          setIsPremium(userData.plan === "pro" || userData.plan === "admin");
          setIsAdmin(userData.plan === "admin");
        } catch {
          setIsPremium(false);
          setIsAdmin(false);
        }
      }
    };
    checkAuth();

    const { data: listener } = supabase.auth.onAuthStateChange(async (_event, session) => {
      setUser(session?.user || null);
      if (session) {
        try {
          const userData = await auth.me();
          setIsPremium(userData.plan === "pro" || userData.plan === "admin");
          setIsAdmin(userData.plan === "admin");
        } catch {
          setIsPremium(false);
          setIsAdmin(false);
        }
      } else {
        setIsPremium(false);
        setIsAdmin(false);
      }
    });

    return () => listener?.subscription.unsubscribe();
  }, []);

  // Keep Render backend alive
  useEffect(() => {
    const ping = () => {
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/health`).catch(() => {});
    };
    ping();
    const interval = setInterval(ping, 4 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  // Load initial data
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      let token: string | undefined;
      if (user) {
        const { data: { session } } = await supabase.auth.getSession();
        token = session?.access_token;
      }
      const result = await disclosures.live(token);
      setItems(result.data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Realtime subscription (new disclosures)
  useEffect(() => {
    const channel = supabase
      .channel("disclosures-live")
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "disclosures" },
        (payload) => {
          const newItem = payload.new as DisclosureItem;
          if (newItem.is_feed_visible) {
            setItems((prev) => [newItem, ...prev].slice(0, 100));
            window.scrollTo({ top: 0, behavior: "smooth" });
          }
        }
      )
      .on(
        "postgres_changes",
        { event: "UPDATE", schema: "public", table: "disclosures" },
        (payload) => {
          const updated = payload.new as DisclosureItem;
          setItems((prev) =>
            prev.map((item) =>
              item.dart_rcept_no === updated.dart_rcept_no ? updated : item
            )
          );
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  // Determine real-time vs delayed display
  const baseItems = useMemo(() => {
    if (isPremium) return items;
    const cutoff = Date.now() - 3 * 60 * 1000;
    return items.filter((it) => {
      return new Date(it.published_at).getTime() <= cutoff;
    });
  }, [items, isPremium]);

  // Apply nature filter
  const displayItems = useMemo(() => {
    if (filter === "all") return baseItems;
    return baseItems.filter((it) => getNature(it) === filter);
  }, [baseItems, filter]);

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-6">
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="card p-5">
              <div className="shimmer h-4 w-24 mb-2" />
              <div className="shimmer h-5 w-3/4 mb-1" />
              <div className="shimmer h-4 w-full" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-6 text-center">
        <AlertCircle size={48} className="text-[var(--accent-red)] mx-auto mb-4" />
        <p className="text-[var(--accent-red)]">{error}</p>
        <button onClick={() => loadData()} className="btn-outline mt-4">
          재시도
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-white">실시간 피드</h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1 flex items-center gap-1.5">
            {isPremium ? (
              <><Crown size={14} className="text-yellow-400" /> 프리미엄 — 실시간</>
            ) : (
              <><Lock size={14} /> 3분 지연 (Pro 가입 시 실시간)</>
            )}
            <span className="text-[var(--text-muted)]">
              &middot; {baseItems.length}개 공시
            </span>
          </p>
        </div>
        <button
          onClick={() => {
            setLoading(true);
            loadData().then(() => setLoading(false));
          }}
          className="btn-outline text-sm py-2 px-4 flex items-center gap-1.5"
        >
          <RefreshCw size={14} />
          새로고침
        </button>
      </div>

      {/* Filter tabs */}
      <div className="flex items-center gap-2 mb-4">
        {FILTER_OPTIONS.map((opt) => (
          <button
            key={opt.key}
            onClick={() => setFilter(opt.key)}
            className={`flex items-center gap-1.5 text-xs font-semibold px-4 py-1.5 rounded-full transition-all ${
              filter === opt.key
                ? opt.key === "positive"
                  ? "bg-green-900/30 text-green-400 border border-green-700/50"
                  : opt.key === "negative"
                  ? "bg-red-900/30 text-red-400 border border-red-700/50"
                  : "bg-[var(--accent-mint)]/10 text-[var(--accent-mint)] border border-[var(--accent-mint)]/30"
                : "text-[var(--text-secondary)] border border-[var(--border-color)] hover:text-white"
            }`}
          >
            {opt.icon && <opt.icon size={12} />}
            {opt.label}
          </button>
        ))}
        {filter !== "all" && (
          <span className="text-[11px] text-[var(--text-muted)] ml-auto">
            {displayItems.length}건
          </span>
        )}
      </div>

      {/* Feed */}
      <div className="space-y-3">
        {displayItems.map((item) => (
          <DisclosureCard key={item.dart_rcept_no} item={item} isAdmin={isAdmin} />
        ))}
      </div>

      {displayItems.length === 0 && (
        <div className="text-center py-16">
          <p className="text-[var(--text-muted)]">아직 공시가 없습니다</p>
        </div>
      )}
    </div>
  );
}
