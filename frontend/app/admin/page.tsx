import { AssistantPanel } from "@/app/_components/assistant-panel";
import { SectionCard } from "@/app/_components/section-card";
import { StatCard } from "@/app/_components/stat-card";
import { StatusPill } from "@/app/_components/status-pill";
import { getAdminOverview } from "@/app/_lib/api";
import { formatDateTime } from "@/app/_lib/format";

export default async function AdminPage() {
  const overview = await getAdminOverview();

  return (
    <div className="space-y-8">
      <section className="grid gap-4 md:grid-cols-4">
        <StatCard eyebrow="Donor accounts" value={overview.donor_count.toString()} detail="Total live supply accounts." />
        <StatCard eyebrow="NGO accounts" value={overview.ngo_count.toString()} detail="Partner organizations visible to dispatch." />
        <StatCard eyebrow="Open requests" value={overview.open_request_count.toString()} detail="Demand still active in the queue." />
        <StatCard eyebrow="Reserved donations" value={overview.reserved_donation_count.toString()} detail="Items already committed but not yet delivered." />
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <SectionCard title="Expiring and in-flight" description="Donations that need immediate admin supervision.">
          <div className="grid gap-3">
            {overview.expiring_donations.map((donation) => (
              <div key={donation.id} className="rounded-[1.5rem] border border-slate-200 bg-slate-50/80 p-4">
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-lg font-semibold text-slate-950">{donation.title}</h3>
                      <StatusPill status={donation.status} />
                    </div>
                    <p className="mt-2 text-sm text-slate-600">{donation.location.area} · {donation.quantity} {donation.unit}</p>
                  </div>
                  <div className="text-sm text-slate-600">Expiry {formatDateTime(donation.expires_at)}</div>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Matching highlights" description="Top ranked routes surfaced by the engine.">
          <div className="grid gap-3">
            {overview.top_matches.map((match, index) => (
  <div
    key={`${match.request_id}-${match.ngo_name}-${index}`}
    className="rounded-[1.5rem] border border-slate-200 bg-white p-4"
  >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="text-lg font-semibold text-slate-950">{match.ngo_name}</h3>
                    <p className="text-sm text-slate-600">{match.request_title}</p>
                  </div>
                  <div className="rounded-2xl bg-slate-950 px-3 py-2 text-sm font-semibold text-white">{match.total_score.toFixed(1)}</div>
                </div>
                <p className="mt-3 text-sm text-slate-600">{match.explanation}</p>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>

      <SectionCard title="Notifications" description="Admin, donor, and NGO alerts emitted by the platform.">
        <div className="grid gap-3">
          {overview.notifications.map((notification) => (
            <div key={notification.id} className="rounded-[1.5rem] border border-slate-200 bg-white p-4">
              <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-slate-950">{notification.title}</h3>
                  <p className="mt-2 text-sm text-slate-600">{notification.message}</p>
                </div>
                <div className="text-sm text-slate-500">{formatDateTime(notification.created_at)}</div>
              </div>
            </div>
          ))}
        </div>
      </SectionCard>

      <AssistantPanel title="Admin AI Copilot" description="Ask for prioritization, route, and waste-risk guidance using the live rescue board." />
    </div>
  );
}
