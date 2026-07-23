"use client";

import { useState, useEffect, useCallback } from "react";
import { supabase } from "@/lib/supabase";
import { disclosures, DisclosureItem } from "@/lib/api";
import DisclosureCard from "@/components/DisclosureCard";
import { RefreshCw, AlertCircle } from "lucide-react";

export default function LivePage() {
  const [items, setItems] = useState<DisclosureItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Keep Render backend alive (ping every 4 min to prevent sleep)
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
      const result = await disclosures.list();
      setItems(result.data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

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
        },
        (payload) => {
          const newItem = payload.new as DisclosureItem;
          setItems((prev) => [newItem, ...prev].slice(0, 100));
          window.scrollTo({ top: 0, behavior: "smooth" });
        }
      )
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "disclosures",
        },
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
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            총 {items.length}개 공시
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
