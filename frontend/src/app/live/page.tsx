"use client";

import { useState, useEffect, useCallback } from "react";
import { supabase } from "@/lib/supabase";
import { disclosures, DisclosureItem, auth } from "@/lib/api";
import DisclosureCard from "@/components/DisclosureCard";
import { RefreshCw, AlertCircle, Lock, Crown } from "lucide-react";

export default function LivePage() {
  const [items, setItems] = useState<DisclosureItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<any>(null);
  const [isPremium, setIsPremium] = useState(false);
  const [delayed, setDelayed] = useState(true);

  // Check auth state + plan from backend API
  useEffect(() => {
    const checkAuth = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      setUser(session?.user || null);
      if (session) {
        try {
          const userData = await auth.me();
          setIsPremium(userData.plan === "pro" || userData.plan === "admin");
        } catch {
          setIsPremium(false);
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
        } catch {
          setIsPremium(false);
        }
      } else {
        setIsPremium(false);
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
          // Only show if feed-visible
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
  const displayItems = isPremium
    ? items
    : items.filter((it) => {
        const cutoff = Date.now() - 3 * 60 * 1000;
        return new Date(it.published_at).getTime() <= cutoff;
      });

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
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-2xl font-bold text-white">실시간 피드</h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1 flex items-center gap-1.5">
            {isPremium ? (
              <><Crown size={14} className="text-yellow-400" /> 프리미엄 — 실시간</>
            ) : (
              <><Lock size={14} /> 3분 지연 (Pro 가입 시 실시간)</>
            )}
            <span className="text-[var(--text-muted)]">
              &middot; {displayItems.length}개 공시
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

      {/* Feed */}
      <div className="space-y-3">
        {displayItems.map((item) => (
          <DisclosureCard key={item.dart_rcept_no} item={item} />
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
