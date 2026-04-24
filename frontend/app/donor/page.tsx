import { SectionCard } from "@/app/_components/section-card";
import { StatCard } from "@/app/_components/stat-card";
import { StatusPill } from "@/app/_components/status-pill";
import { getDashboardBundle } from "@/app/_lib/api";
import { requireAuth } from "@/app/_lib/auth-server";

export default async function DonorPage() {
  const currentUser = await requireAuth("donor");
  const { donors, donations } = await getDashboardBundle();

  const donorRows = donors
    .filter((donor) => donor.id === currentUser.profile_id)
    .map((donor) => {
      const donorDonations = donations.filter((donation) => donation.donor_id === donor.id);
      const deliveredMeals = donorDonations
        .filter((donation) => donation.status === "delivered")
        .reduce((total, donation) => total + donation.meals_estimate, 0);
      const activeCount = donorDonations.filter((donation) => ["available", "requested", "reserved", "picked_up"].includes(donation.status)).length;

      return {
        donor,
        donorDonations,
        deliveredMeals,
        activeCount,
      };
    });

  const scopedDonations = donorRows.flatMap((row) => row.donorDonations);

  return (
    <div className="space-y-8">
      <section className="grid gap-4 md:grid-cols-3">
        <StatCard eyebrow="Donor account" value={donorRows.length.toString()} detail="Authenticated donor profile currently in scope." />
        <StatCard eyebrow="Active listings" value={scopedDonations.filter((donation) => ["available", "requested", "reserved", "picked_up"].includes(donation.status)).length.toString()} detail="Your stock that still needs matching or delivery." />
        <StatCard eyebrow="Delivered meals" value={scopedDonations.filter((donation) => donation.status === "delivered").reduce((total, donation) => total + donation.meals_estimate, 0).toString()} detail="Meals already completed from your inventory." />
      </section>

      <SectionCard title="Donor dashboard" description="Reliability and dispatch readiness by donor account.">
        <div className="grid gap-4 xl:grid-cols-3">
          {donorRows.map(({ donor, donorDonations, deliveredMeals, activeCount }) => (
            <div key={donor.id} className="rounded-[1.7rem] border border-slate-200 bg-slate-50/80 p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-xl font-semibold text-slate-950">{donor.name}</h3>
                  <p className="mt-1 text-sm text-slate-600">{donor.location.area} · {donor.donor_type.replaceAll("_", " ")}</p>
                </div>
                <div className="rounded-2xl bg-slate-950 px-3 py-2 text-sm font-semibold text-white">{donor.reliability}%</div>
              </div>
              <div className="mt-5 grid gap-3 text-sm text-slate-600">
                <div className="rounded-2xl bg-white p-3">Preferred radius: <span className="font-semibold text-slate-950">{donor.preferred_radius_km} km</span></div>
                <div className="rounded-2xl bg-white p-3">Active listings: <span className="font-semibold text-slate-950">{activeCount}</span></div>
                <div className="rounded-2xl bg-white p-3">Delivered meals: <span className="font-semibold text-slate-950">{deliveredMeals}</span></div>
              </div>
              <div className="mt-5 space-y-3">
                {donorDonations.slice(0, 3).map((donation) => (
                  <div key={donation.id} className="rounded-2xl border border-slate-200 bg-white p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-slate-950">{donation.title}</span>
                      <StatusPill status={donation.status} />
                    </div>
                    <p className="mt-2 text-sm text-slate-600">{donation.quantity} {donation.unit} · {donation.location.area}</p>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </SectionCard>
    </div>
  );
}
