import { DonationWorkbench } from "@/app/_components/donation-workbench";
import { SectionCard } from "@/app/_components/section-card";
import { StatCard } from "@/app/_components/stat-card";
import { getDashboardBundle, getMatchesIndex } from "@/app/_lib/api";
import { requireAuth } from "@/app/_lib/auth-server";

export default async function DonationsPage() {
  const currentUser = await requireAuth("donor");

  const { donors, ngos, donations: allDonations, requests } = await getDashboardBundle();
  const donorsForUser = donors.filter((donor) => donor.id === currentUser.profile_id);
  const donations = allDonations.filter((donation) => donation.donor_id === currentUser.profile_id);
  const candidateIds = donations.filter((donation) => ["available", "reserved", "picked_up"].includes(donation.status)).map((donation) => donation.id);
  const initialMatchesByDonationId = await getMatchesIndex(candidateIds);

  return (
    <div className="space-y-8">
      <section className="grid gap-4 md:grid-cols-4">
        <StatCard eyebrow="Listings" value={donations.length.toString()} detail="All donation records in the current board." />
        <StatCard eyebrow="Available now" value={donations.filter((donation) => donation.status === "available").length.toString()} detail="Fresh inventory waiting for an NGO decision." />
        <StatCard eyebrow="Reserved" value={donations.filter((donation) => donation.status === "reserved").length.toString()} detail="Supply already committed to a request." />
        <StatCard eyebrow="Picked up" value={donations.filter((donation) => donation.status === "picked_up").length.toString()} detail="Dispatches that are currently on the road." />
      </section>

      <SectionCard title="Donations workspace" description="Creation form, donation list, map view, and matching explanation panel.">
        <DonationWorkbench
          donors={donorsForUser}
          ngos={ngos}
          donations={donations}
          requests={requests}
          initialMatchesByDonationId={initialMatchesByDonationId}
        />
      </SectionCard>
    </div>
  );
}
