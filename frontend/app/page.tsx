import Link from "next/link";

import { AssistantPanel } from "@/app/_components/assistant-panel";
import { OverviewAIInsights } from "@/app/_components/overview-ai-insights";
import { SectionCard } from "@/app/_components/section-card";
import { StatCard } from "@/app/_components/stat-card";
import { StatusPill } from "@/app/_components/status-pill";
import { getDashboardBundle } from "@/app/_lib/api";
import { formatDateTime, formatPercent } from "@/app/_lib/format";

export default async function Page() {
  const { admin, impact, donations, requests } = await getDashboardBundle();
  const urgentDonations = donations.filter((donation) => ["available", "reserved", "picked_up"].includes(donation.status)).slice(0, 4);
  const liveRequests = requests.filter((request) => ["open", "requested", "matched", "reserved"].includes(request.status)).slice(0, 4);

  return (
    <div className="space-y-8">
      <section className="grid gap-6 lg:grid-cols-[1.25fr_0.95fr]">
        <div className="rounded-[2.2rem] bg-slate-950 px-7 py-8 text-white shadow-lg shadow-slate-950/15">
          <p className="text-xs font-semibold uppercase tracking-[0.32em] text-sky-300">Live overview</p>
          <h2 className="mt-4 max-w-2xl text-4xl font-semibold tracking-tight">See supply, demand, and rescue confidence in one operating view.</h2>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300">
            The backend seed mirrors live Hyderabad corridors so donor teams can post inventory fast, NGOs can surface demand, and admins can see exactly why the engine routes a donation to a given request.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/donations" className="rounded-full bg-white px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-slate-100">
              Open donations workspace
            </Link>
            <Link href="/admin" className="rounded-full border border-white/20 px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/8">
              Review admin board
            </Link>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
          <StatCard eyebrow="Meals recovered" value={impact.meals_recovered.toString()} detail="Meals successfully delivered in the demo snapshot." accent="Recovered" />
          <StatCard eyebrow="Success rate" value={formatPercent(impact.delivery_success_rate)} detail="Share of completed donation outcomes that ended in delivery." accent="Fulfilment" />
          <StatCard eyebrow="Open demand" value={admin.open_request_count.toString()} detail="Requests still in play for matching, reservation, or delivery." accent="Active lanes" />
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard eyebrow="Donors" value={admin.donor_count.toString()} detail="Live donor accounts in the Hyderabad seed." />
        <StatCard eyebrow="NGOs" value={admin.ngo_count.toString()} detail="Partner organizations currently receiving or requesting stock." />
        <StatCard eyebrow="Active donations" value={impact.active_donations.toString()} detail="Available, reserved, or already picked up listings." />
        <StatCard eyebrow="CO2e avoided" value={`${impact.co2e_avoided_kg} kg`} detail="Estimated diversion impact from delivered donations." />
      </section>

      <OverviewAIInsights donations={donations} />

      <div className="grid gap-6 xl:grid-cols-[1.1fr_1fr]">
        <SectionCard title="Urgent donations" description="Items closest to expiry or already in motion.">
          <div className="grid gap-3">
            {urgentDonations.map((donation) => (
              <div key={donation.id} className="rounded-[1.5rem] border border-slate-200 bg-slate-50/80 p-4">
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-lg font-semibold text-slate-950">{donation.title}</h3>
                      <StatusPill status={donation.status} />
                    </div>
                    <p className="mt-2 text-sm text-slate-600">{donation.location.area} · {donation.quantity} {donation.unit}</p>
                  </div>
                  <div className="text-sm text-slate-600">Expires {formatDateTime(donation.expires_at)}</div>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Live NGO demand" description="Requests still driving the matching queue.">
          <div className="grid gap-3">
            {liveRequests.map((request) => (
              <div key={request.id} className="rounded-[1.5rem] border border-slate-200 bg-white p-4">
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-lg font-semibold text-slate-950">{request.title}</h3>
                      <StatusPill status={request.status} />
                    </div>
                    <p className="mt-2 text-sm text-slate-600">Priority {request.priority} · {request.location.area} · {request.people_served} people</p>
                  </div>
                  <div className="text-sm text-slate-600">Needed {formatDateTime(request.needed_by)}</div>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>

      <SectionCard title="Quick routes" description="Jump straight into the operating area you need.">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          {[
            ["Donor dashboard", "/donor", "Reliability, donation cadence, and pickup-ready stock by donor."],
            ["NGO dashboard", "/ngo", "Capacity, active requests, and intake pressure by partner."],
            ["Donations workspace", "/donations", "Create listings, browse list/map view, and inspect match logic."],
            ["Admin dashboard", "/admin", "Expiring items, notifications, and top routing decisions."],
            ["Impact dashboard", "/impact", "Recovery, diversion, and fulfilment metrics over the current seed."],
          ].map(([title, href, description]) => (
            <Link key={href} href={href} className="rounded-[1.6rem] border border-slate-200 bg-slate-50/80 p-5 transition hover:border-slate-300 hover:bg-white">
              <h3 className="text-lg font-semibold text-slate-950">{title}</h3>
              <p className="mt-2 text-sm text-slate-600">{description}</p>
            </Link>
          ))}
        </div>
      </SectionCard>

      <AssistantPanel />
    </div>
  );
}
