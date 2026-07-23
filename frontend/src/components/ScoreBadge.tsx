"use client";

interface ScoreBadgeProps {
  score: number | null;
  size?: "sm" | "md" | "lg";
}

export default function ScoreBadge({ score, size = "md" }: ScoreBadgeProps) {
  if (score === null) {
    return (
      <span
        className={`inline-flex items-center justify-center font-mono font-bold rounded ${
          size === "sm" ? "text-[10px] px-1.5 py-0.5" : size === "lg" ? "text-lg px-3 py-1" : "text-sm px-2 py-0.5"
        } bg-[var(--bg-hover)] text-[var(--text-muted)]`}
      >
        --
      </span>
    );
  }

  const colorClass = score >= 70 ? "score-high" : score >= 40 ? "score-mid" : "score-low";
  const bgClass = score >= 70 ? "bg-green-900/30" : score >= 40 ? "bg-yellow-900/30" : "bg-red-900/30";

  return (
    <span
      className={`inline-flex items-center justify-center font-mono font-bold rounded ${colorClass} ${bgClass} ${
        size === "sm" ? "text-[10px] px-1.5 py-0.5" : size === "lg" ? "text-lg px-3 py-1" : "text-sm px-2 py-0.5"
      }`}
    >
      {Math.round(score)}
    </span>
  );
}
