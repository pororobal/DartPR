"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import Link from "next/link";
import { Lock } from "lucide-react";

interface PlanGuardProps {
  requiredPlan: "pro" | "developer";
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export default function PlanGuard({ requiredPlan, children, fallback }: PlanGuardProps) {
  const [plan, setPlan] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const check = async () => {
      const { data } = await supabase.auth.getSession();
      if (!data.session) {
        setPlan(null);
        setLoading(false);
        return;
      }

      const res = await fetch("/api/v1/auth/me", {
        headers: {
          Authorization: `Bearer ${data.session.access_token}`,
        },
      });

      if (res.ok) {
        const user = await res.json();
        setPlan(user.plan);
      } else {
        setPlan("free");
      }
      setLoading(false);
    };

    check();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="shimmer h-8 w-32" />
      </div>
    );
  }

  const planRank: Record<string, number> = { free: 0, pro: 1, developer: 2 };
  const requiredRank = planRank[requiredPlan] || 1;

  if (!plan || (planRank[plan] ?? 0) < requiredRank) {
    if (fallback) return <>{fallback}</>;

    return (
      <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
        <Lock size={48} className="text-[var(--text-muted)] mb-4" />
        <h2 className="text-xl font-bold text-white mb-2">플랜 업그레이드 필요</h2>
        <p className="text-sm text-[var(--text-secondary)] mb-6 max-w-md">
          {requiredPlan === "pro"
            ? "실시간 피드는 Pro 플랜 이상부터 이용 가능합니다."
            : "Developer 플랜이 필요합니다."}
        </p>
        <Link href="/pricing" className="btn-primary">
          플랜 보기
        </Link>
      </div>
    );
  }

  return <>{children}</>;
}
