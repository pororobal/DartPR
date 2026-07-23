"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { supabase } from "@/lib/supabase";
import { disclosures, DisclosureItem } from "@/lib/api";
import DisclosureCard from "@/components/DisclosureCard";
import { RefreshCw, AlertCircle } from "lucide-react";

export default function LivePage() {
  const [items, setItems] = useState<DisclosureItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isFreeTier, setIsFreeTier] = useState(false);
  const [isLive, setIsLive] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Load initial data
  const loadData = useCallback(async () => {
    try {
      const { data: session } = await supabase.auth.getSession();
      const hasSession = !!session?.session;
      setIsFreeTier(!hasSession);

      if (hasSession) {
        // Check plan
        const res = await fetch("/api/v1/auth/me", {
          headers: {
            Authorization: `Bearer ${session.session!.access_token}`,
          },
        });
        if (res.ok) {
          const user = await res.json();
          if (user.plan === "free") {
            setIsFreeTier(true);
          } else {
            setIsLive(true);
          }
        }
      }

      // Fetch initial data
      const endpoint = hasSession && !isFreeTier ? disclosures.live : disclosures.delayed;
      const result = await endpoint();
      setItems(result.data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, [isFreeTier]);

  useEffect(() => {
    loadData();
  }, []);

  // Supabase Realtime subscription
  useEffect(() => {
    const channel = supabase
      .channel("disclosures-live")
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "disclosures",
          filter: "is_feed_visible=eq.true",
        },
        (payload) => {
          const newItem = payload.new as DisclosureItem;
          setItems((prev) => [newItem, ...prev].slice(0, 100));
          // Scroll to top on new item
          window.scrollTo({ top: 0, behavior: "smooth" });
        }
      )
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "disclosures",
          filter: "is_feed_visible=eq.true",
        },
        (payload) => {
          const updated = payload.new as DisclosureItem;
          setItems((prev) =>
            prev.map((item) => (item.dart_rcept_no === updated.dart_rcept_no ? updated : item))
          );
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-8">
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="card p-4">
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
      <div className="max-w-3xl mx-auto px-4 py-8 text-center">
        <AlertCircle size={48} className="text-[var(--accent-red)] mx-auto mb-4" />
        <p className="text-[var(--accent-red)]">{error}</p>
        <button onClick={loadData} className="btn-outline mt-4">
          재시도
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8" ref={containerRef}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-white">실시간 피드</h1>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            {items.length}개 공시 · {isFreeTier ? "3분 지연" : "실시간"}
          </p>
        </div>
        <button
          onClick={() => {
            setLoading(true);
            loadData().then(() => setLoading(false));
          }}
          className="btn-outline text-xs py-1.5 px-3 flex items-center gap-1"
        >
          <RefreshCw size={12} />
          새로고침
        </button>
      </div>

      {/* Free tier banner */}
      {isFreeTier && (
        <div className="bg-yellow-900/20 border border-yellow-800/40 rounded-lg p-3 mb-4 flex items-center gap-2">
          <AlertCircle size={14} className="text-yellow-500 flex-shrink-0" />
          <p className="text-xs text-yellow-400">
            Free 플랜은 3분 지연됩니다.{" "}
            <a href="/pricing" className="underline">
              업그레이드하기
            </a>
          </p>
        </div>
      )}

      {/* Live indicator */}
      {isLive && (
        <div className="flex items-center gap-2 mb-4">
          <span className="w-2 h-2 rounded-full bg-[var(--accent-mint)] animate-pulse" />
          <span className="text-[10px] text-[var(--accent-mint)] font-bold uppercase tracking-widest">
            LIVE
          </span>
        </div>
      )}

      {/* Feed */}
      <div className="space-y-3">
        {items.map((item) => (
          <DisclosureCard key={item.dart_rcept_no} item={item} />
        ))}
      </div>

      {items.length === 0 && (
        <div className="text-center py-16">
          <p className="text-[var(--text-muted)]">아직 공시가 없습니다</p>
        </div>
      )}
    </div>
  );
}
