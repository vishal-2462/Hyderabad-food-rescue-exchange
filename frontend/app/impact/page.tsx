import { ImpactIntelligenceDashboard } from "@/app/_components/impact-intelligence-dashboard";
import { SectionCard } from "@/app/_components/section-card";
import { StatCard } from "@/app/_components/stat-card";
import { getDashboardBundle } from "@/app/_lib/api";
import { formatPercent } from "@/app/_lib/format";

export default async function ImpactPage() {
  const { donations, impact, requests } = await getDashboardBundle();

  const lifecycleCounts = {
    available: donations.filter((donation) => donation.status === "available").length,
    reserved: donations.filter((donation) => donation.status === "reserved").length,
    picked_up: donations.filter((donation) => donation.status === "picked_up").length,
    delivered: donations.filter((donation) => donation.status === "delivered").length,
    expired: donations.filter((donation) => donation.status === "expired").length,
    cancelled: donations.filter((donation) => donation.status === "cancelled").length,
  };

  return (
    <div className="space-y-8">
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <StatCard eyebrow="Meals recovered" value={impact.meals_recovered.toString()} detail="Delivered meals in the current snapshot." />
        <StatCard eyebrow="Delivered donations" value={impact.delivered_donations.toString()} detail="Completed last-mile dispatches." />
        <StatCard eyebrow="Open requests" value={impact.open_requests.toString()} detail="Demand lanes still live." />
        <StatCard eyebrow="Fulfilled requests" value={impact.fulfilled_requests.toString()} detail="Requests closed successfully." />
        <StatCard eyebrow="Success rate" value={formatPercent(impact.delivery_success_rate)} detail="Delivered share of all completed outcomes." />
      </section>

      <div className="grid gap-6 xl:grid-cols-[1fr_1.05fr]">
        <SectionCard title="Impact dashboard" description="Recovery, diversion, and network activity from the backend metrics endpoint.">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-[1.6rem] bg-slate-950 p-5 text-white">
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-sky-300">Diversion</p>
              <p className="mt-3 text-4xl font-semibold">{impact.co2e_avoided_kg} kg</p>
              <p className="mt-2 text-sm text-slate-300">Estimated CO2e avoided through successful deliveries.</p>
            </div>
            <div className="rounded-[1.6rem] bg-white p-5 ring-1 ring-slate-200">
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Active network</p>
              <p className="mt-3 text-4xl font-semibold text-slate-950">{impact.donors_active + impact.ngos_active}</p>
              <p className="mt-2 text-sm text-slate-600">Combined active donors and NGOs participating in the current board.</p>
            </div>
            <div className="rounded-[1.6rem] bg-white p-5 ring-1 ring-slate-200">
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Recovered quantity</p>
              <p className="mt-3 text-4xl font-semibold text-slate-950">{impact.total_quantity_kg}</p>
              <p className="mt-2 text-sm text-slate-600">Quantity attributed to delivered donation records.</p>
            </div>
            <div className="rounded-[1.6rem] bg-white p-5 ring-1 ring-slate-200">
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Request coverage</p>
              <p className="mt-3 text-4xl font-semibold text-slate-950">{requests.length}</p>
              <p className="mt-2 text-sm text-slate-600">Total demand records visible to the matching engine.</p>
            </div>
          </div>
        </SectionCard>

        <SectionCard title="Lifecycle mix" description="How inventory is distributed across the donation lifecycle.">
          <div className="space-y-4">
            {Object.entries(lifecycleCounts).map(([label, value]) => {
              const share = (value / Math.max(donations.length, 1)) * 100;
              return (
                <div key={label} className="space-y-2">
                  <div className="flex items-center justify-between text-sm font-medium text-slate-700">
                    <span className="capitalize">{label.replaceAll("_", " ")}</span>
                    <span>{value}</span>
                  </div>
                  <div className="h-3 rounded-full bg-slate-100">
                    <div className="h-3 rounded-full bg-gradient-to-r from-sky-500 via-indigo-500 to-violet-500" style={{ width: `${share}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </SectionCard>
      </div>

      <ImpactIntelligenceDashboard />
    </div>
  );
}
