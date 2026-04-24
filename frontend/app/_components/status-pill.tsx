import { formatStatusLabel } from "@/app/_lib/format";
import type { DonationStatus, RequestStatus } from "@/app/_lib/types";

const tones: Record<string, string> = {
  available: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  requested: "bg-amber-50 text-amber-700 ring-amber-200",
  reserved: "bg-sky-50 text-sky-700 ring-sky-200",
  picked_up: "bg-violet-50 text-violet-700 ring-violet-200",
  delivered: "bg-emerald-100 text-emerald-800 ring-emerald-200",
  expired: "bg-slate-100 text-slate-600 ring-slate-200",
  cancelled: "bg-rose-50 text-rose-700 ring-rose-200",
  open: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  matched: "bg-sky-50 text-sky-700 ring-sky-200",
  fulfilled: "bg-indigo-50 text-indigo-700 ring-indigo-200",
  rejected: "bg-rose-50 text-rose-700 ring-rose-200",
};

export function StatusPill({ status }: { status: DonationStatus | RequestStatus }) {
  return (
    <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold capitalize ring-1 ${tones[status] ?? tones.open}`}>
      {formatStatusLabel(status)}
    </span>
  );
}
