import Link from "next/link";

export default function Footer() {
  return (
    <footer className="border-t border-[var(--border-color)] py-8 mt-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="text-sm text-[var(--text-muted)]">
            <span className="text-[var(--accent-mint)]">Dart</span>PR &copy; {new Date().getFullYear()}
          </div>
          <div className="flex items-center gap-4 text-xs text-[var(--text-muted)]">
            <Link href="/pricing" className="hover:text-[var(--text-secondary)] transition-colors">
              플랜
            </Link>
            <span>데이터 출처: OpenDART</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
