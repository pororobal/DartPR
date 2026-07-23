import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: "DART0s — 실시간 공시 분석 플랫폼",
  description: "DART 공시를 LLM이 분석하고 DVI 점수로 환산합니다. 실시간 트레이딩 인사이트.",
  openGraph: {
    title: "DART0s — 실시간 공시 분석",
    description: "DART 공시를 LLM이 분석하고 점수화합니다.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko" className="h-full">
      <body className="min-h-full flex flex-col bg-[var(--bg-primary)] text-[var(--text-primary)]">
        <Navbar />
        <main className="flex-1 pt-16">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
