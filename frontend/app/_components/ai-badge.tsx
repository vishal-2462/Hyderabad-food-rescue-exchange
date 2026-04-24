import type { ReactNode } from "react";

const tones: Record<string, string> = {
  sky: "border-sky-200 bg-sky-50 text-sky-700",
  emerald: "border-emerald-200 bg-emerald-50 text-emerald-700",
  amber: "border-amber-200 bg-amber-50 text-amber-700",
  rose: "border-rose-200 bg-rose-50 text-rose-700",
  violet: "border-violet-200 bg-violet-50 text-violet-700",
  slate: "border-slate-200 bg-slate-50 text-slate-700",
};

export function AIBadge({ label, tone = "sky", detail }: { label: string; tone?: keyof typeof tones; detail?: ReactNode }) {
  return (
    <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold ${tones[tone] ?? tones.sky}`}>
      <span>{label}</span>
      {detail ? <span className="font-medium opacity-80">{detail}</span> : null}
    </span>
  );
}
