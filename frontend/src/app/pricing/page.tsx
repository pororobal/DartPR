"use client";

import PricingTable from "@/components/PricingTable";

export default function PricingPage() {
  return (
    <div className="max-w-5xl mx-auto px-4 py-12">
      <div className="text-center mb-10">
        <h1 className="text-2xl font-bold text-white">플랜</h1>
        <p className="text-sm text-[var(--text-secondary)] mt-2 max-w-lg mx-auto">
          결제는 카카오톡 오픈프로필로 문의 주시면 관리자가 수동으로 플랜을 변경해드립니다.
        </p>
      </div>
      <PricingTable />
    </div>
  );
}
