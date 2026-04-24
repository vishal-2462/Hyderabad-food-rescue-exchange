import { API_BASE_URL } from "@/app/_lib/api-config";
import {
  demoAdminOverview,
  demoDonations,
  demoDonors,
  demoImpactMetrics,
  demoMatchesByDonationId,
  demoNgos,
  demoRequests,
} from "@/app/_lib/demo-data";
import type { AdminOverview, DashboardBundle, Donation, Donor, ImpactMetrics, MatchCandidate, NGO, AidRequest } from "@/app/_lib/types";

async function fetchJson<T>(path: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Request failed with ${response.status}`);
    }
    return (await response.json()) as T;
  } catch {
    return fallback;
  }
}

export async function getDonors(): Promise<Donor[]> {
  return fetchJson("/donors", demoDonors);
}

export async function getNgos(): Promise<NGO[]> {
  return fetchJson("/ngos", demoNgos);
}

export async function getDonations(): Promise<Donation[]> {
  return fetchJson("/donations", demoDonations);
}

export async function getRequests(): Promise<AidRequest[]> {
  return fetchJson("/requests", demoRequests);
}

export async function getImpactMetrics(): Promise<ImpactMetrics> {
  return fetchJson("/impact/metrics", demoImpactMetrics);
}

export async function getAdminOverview(): Promise<AdminOverview> {
  return fetchJson("/admin/overview", demoAdminOverview);
}

export async function getDonationMatches(donationId: string): Promise<MatchCandidate[]> {
  return fetchJson(`/donations/${donationId}/matches`, demoMatchesByDonationId[donationId] ?? []);
}

export async function getDashboardBundle(): Promise<DashboardBundle> {
  const [donors, ngos, donations, requests, impact, admin] = await Promise.all([
    getDonors(),
    getNgos(),
    getDonations(),
    getRequests(),
    getImpactMetrics(),
    getAdminOverview(),
  ]);

  return { donors, ngos, donations, requests, impact, admin };
}

export async function getMatchesIndex(donationIds: string[]): Promise<Record<string, MatchCandidate[]>> {
  const entries = await Promise.all(
    donationIds.map(async (donationId) => [donationId, await getDonationMatches(donationId)] as const),
  );

  return Object.fromEntries(entries);
}
