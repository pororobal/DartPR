"use client";

import PricingTable from "@/components/PricingTable";

export default function PricingPage() {
  return (
    <div className="max-w-5xl mx-auto px-4 py-12">
      <div className="text-center mb-10">
        <h1 className="text-2xl font-bold text-white">플랜</h1>
        <p className="text-sm text-[var(--text-secondary)] mt-2 max-w-lg mx-auto">
          Pro 플랜을 원하시면 아래 카카오톡 오픈프로필을 클릭해주세요.
        </p>
      </div>
      <PricingTable />
    </div>
  );
}
