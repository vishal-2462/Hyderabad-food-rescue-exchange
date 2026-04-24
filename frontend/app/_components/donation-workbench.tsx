"use client";

import { useEffect, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { AIBadge } from "@/app/_components/ai-badge";
import { DonationIntelligencePanel } from "@/app/_components/donation-intelligence-panel";
import { FoodImageAnalyzer } from "@/app/_components/food-image-analyzer";
import { createAuthorizedRequestInit } from "@/app/_lib/auth-client";
import { getWasteRisk, predictExpiryForDonation } from "@/app/_lib/ai";
import { API_BASE_URL } from "@/app/_lib/api-config";
import { formatDateTime, formatStatusLabel } from "@/app/_lib/format";
import type { AidRequest, Donation, DonationCreatePayload, Donor, ExpiryPredictionResponse, FoodImageAnalysisResponse, ImageFreshnessLabel, MatchCandidate, NGO, RequestApprovalPayload, WasteRiskResponse } from "@/app/_lib/types";

type ViewMode = "list" | "map";
type SortMode = "ai_priority" | "newest";

type MatchesIndex = Record<string, MatchCandidate[]>;

type FormState = {
  donor_id: string;
  title: string;
  category: string;
  food_type: string;
  prepared_time: string;
  storage_condition: string;
  quantity: string;
  unit: string;
  meals_estimate: string;
  safety_window_hours: string;
  shelf_life_hours: string;
  pickup_start: string;
  pickup_end: string;
  image_freshness_label: ImageFreshnessLabel | "";
  image_visual_label: string;
  image_visual_confidence: string;
  notes: string;
};

const SHELF_LIFE_BY_FOOD_TYPE: Record<string, number> = {
  biryani: 5,
  fruit: 8,
  haleem: 3,
  curry: 5,
  rice: 5,
  chicken_curry: 5,
  naan: 2,
  bread_or_bakery: 12,
  dessert: 6,
  fried_rice: 5,
  kebab: 4,
  double_ka_meetha: 6,
  dry_rations: 72,
};

const STORAGE_MULTIPLIERS: Record<string, number> = {
  ambient: 1,
  insulated: 1.08,
  chilled: 1.22,
  frozen: 1.5,
};

function toDatetimeLocal(value: Date) {
  return new Date(value.getTime() - value.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
}

function defaultForm(donors: Donor[]): FormState {
  const base = new Date();
  return {
    donor_id: donors[0]?.id ?? "",
    title: "",
    category: "prepared_food",
    food_type: "biryani",
    prepared_time: toDatetimeLocal(new Date(base.getTime() - 30 * 60 * 1000)),
    storage_condition: "insulated",
    quantity: "60",
    unit: "meal_boxes",
    meals_estimate: "60",
    safety_window_hours: "2",
    shelf_life_hours: "",
    pickup_start: toDatetimeLocal(new Date(base.getTime() + 30 * 60 * 1000)),
    pickup_end: toDatetimeLocal(new Date(base.getTime() + 2 * 60 * 60 * 1000)),
    image_freshness_label: "",
    image_visual_label: "",
    image_visual_confidence: "",
    notes: "Freshly packed and ready for dispatch.",
  };
}

function inferShelfLifeHours(foodType: string, storageCondition: string, override: string): number {
  const baseShelfLife = override ? Number(override) : SHELF_LIFE_BY_FOOD_TYPE[foodType] ?? 6;
  const multiplier = STORAGE_MULTIPLIERS[storageCondition] ?? 1;
  return Number((baseShelfLife * multiplier).toFixed(2));
}

function computeSafeUntil(form: FormState): string {
  const preparedAt = new Date(form.prepared_time);
  const shelfLifeHours = inferShelfLifeHours(form.food_type, form.storage_condition, form.shelf_life_hours);
  return new Date(preparedAt.getTime() + shelfLifeHours * 60 * 60 * 1000).toISOString();
}

function computeSafeUntilFromPayload(payload: DonationCreatePayload): string {
  const preparedAt = new Date(payload.prepared_time);
  const shelfLifeHours = inferShelfLifeHours(payload.food_type, payload.storage_condition, payload.shelf_life_hours?.toString() ?? "");
  return new Date(preparedAt.getTime() + shelfLifeHours * 60 * 60 * 1000).toISOString();
}

function freshnessPriorityRank(analysis: ExpiryPredictionResponse | undefined): number {
  if (!analysis) {
    return 3;
  }
  if (analysis.final_status === "unsafe") {
    return 0;
  }
  if (analysis.final_status === "urgent") {
    return 1;
  }
  return 2;
}

function inferFoodTypeFromImage(analysis: FoodImageAnalysisResponse): string {
  if (analysis.food_category === "fruit") {
    return "fruit";
  }
  if (analysis.food_category === "bread_or_bakery") {
    return "bread_or_bakery";
  }
  if (analysis.food_category === "curry") {
    return "curry";
  }
  if (analysis.food_category === "rice") {
    return "rice";
  }
  if (analysis.food_category === "dessert") {
    return "dessert";
  }
  const guess = analysis.food_type_guess.toLowerCase();
  if (guess.includes("biryani")) {
    return "biryani";
  }
  if (guess.includes("haleem")) {
    return "haleem";
  }
  if (guess.includes("curry")) {
    return "chicken_curry";
  }
  if (guess.includes("naan") || guess.includes("bread")) {
    return "naan";
  }
  if (guess.includes("fried rice") || guess.includes("rice")) {
    return "fried_rice";
  }
  if (guess.includes("kebab")) {
    return "kebab";
  }
  if (guess.includes("meetha")) {
    return "double_ka_meetha";
  }
  if (analysis.food_category === "dry_rations") {
    return "dry_rations";
  }
  return "biryani";
}

function inferDomainCategoryFromFoodCategory(foodCategory: string): string {
  if (foodCategory === "dry_rations") {
    return "dry_rations";
  }
  if (foodCategory === "bread_or_bakery" || foodCategory === "dessert") {
    return "bakery";
  }
  return "prepared_food";
}

function tone(status: string) {
  const tones: Record<string, string> = {
    available: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    requested: "bg-amber-50 text-amber-700 ring-amber-200",
    open: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    matched: "bg-sky-50 text-sky-700 ring-sky-200",
    reserved: "bg-sky-50 text-sky-700 ring-sky-200",
    picked_up: "bg-violet-50 text-violet-700 ring-violet-200",
    fulfilled: "bg-indigo-50 text-indigo-700 ring-indigo-200",
    rejected: "bg-rose-50 text-rose-700 ring-rose-200",
    delivered: "bg-emerald-100 text-emerald-800 ring-emerald-200",
    expired: "bg-slate-100 text-slate-600 ring-slate-200",
    cancelled: "bg-rose-50 text-rose-700 ring-rose-200",
  };

  return tones[status] ?? tones.available;
}

function FactorBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs font-medium text-slate-600">
        <span>{label}</span>
        <span>{value.toFixed(1)}%</span>
      </div>
      <div className="h-2 rounded-full bg-slate-100">
        <div
          className="h-2 rounded-full bg-gradient-to-r from-sky-500 via-indigo-500 to-violet-500"
          style={{ width: `${Math.min(value, 100)}%` }}
        />
      </div>
    </div>
  );
}

async function fetchDonationMatchesFromApi(donationId: string): Promise<MatchCandidate[]> {
  const response = await fetch(`${API_BASE_URL}/donations/${donationId}/matches`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Match lookup failed");
  }

  return (await response.json()) as MatchCandidate[];
}

function MapCanvas({
  donations,
  ngos,
  selectedDonation,
  matches,
  onSelect,
}: {
  donations: Donation[];
  ngos: NGO[];
  selectedDonation: Donation | undefined;
  matches: MatchCandidate[];
  onSelect: (donationId: string) => void;
}) {
  const activeDonations = donations.filter((donation) => ["available", "requested", "reserved", "picked_up"].includes(donation.status));
  const matchedNgos = matches.map((match) => ngos.find((ngo) => ngo.id === match.ngo_id)).filter(Boolean) as NGO[];
  const points = [...activeDonations.map((donation) => donation.location), ...matchedNgos.map((ngo) => ngo.location)];

  const latitudes = points.map((point) => point.lat);
  const longitudes = points.map((point) => point.lng);
  const minLat = Math.min(...latitudes, 17.24);
  const maxLat = Math.max(...latitudes, 17.52);
  const minLng = Math.min(...longitudes, 78.34);
  const maxLng = Math.max(...longitudes, 78.56);

  const project = (lat: number, lng: number) => ({
    left: `${((lng - minLng) / Math.max(maxLng - minLng, 0.01)) * 100}%`,
    top: `${100 - ((lat - minLat) / Math.max(maxLat - minLat, 0.01)) * 100}%`,
  });

  return (
    <div className="rounded-[2rem] border border-slate-200 bg-slate-950 p-4 text-white shadow-lg shadow-slate-950/15">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-400">Hyderabad map view</p>
          <h3 className="text-lg font-semibold text-white">Donation footprint</h3>
        </div>
        <p className="text-sm text-slate-300">Donations in teal, matched NGOs in amber</p>
      </div>
      <div className="relative h-[22rem] overflow-hidden rounded-[1.5rem] border border-white/10 bg-slate-900 bg-[linear-gradient(rgba(255,255,255,0.06)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.06)_1px,transparent_1px)] bg-[size:3.5rem_3.5rem]">
        {activeDonations.map((donation) => {
          const point = project(donation.location.lat, donation.location.lng);
          const selected = donation.id === selectedDonation?.id;

          return (
            <button
              key={donation.id}
              type="button"
              onClick={() => onSelect(donation.id)}
              className={`absolute -translate-x-1/2 -translate-y-1/2 rounded-full border px-3 py-2 text-left text-xs shadow-sm transition ${
                selected
                  ? "border-sky-200 bg-sky-400/20 text-white"
                  : "border-sky-400/20 bg-sky-400/12 text-sky-100 hover:bg-sky-400/18"
              }`}
              style={point}
            >
              <div className="font-semibold">{donation.location.area}</div>
              <div className="text-[11px] text-sky-100/80">{donation.title}</div>
            </button>
          );
        })}
        {matchedNgos.map((ngo) => {
          const point = project(ngo.location.lat, ngo.location.lng);
          return (
            <div
              key={ngo.id}
              className="absolute -translate-x-1/2 -translate-y-1/2 rounded-full border border-amber-300/20 bg-amber-400/15 px-3 py-2 text-xs text-amber-100 shadow-sm"
              style={point}
            >
              <div className="font-semibold">{ngo.location.area}</div>
              <div className="text-[11px] text-amber-100/80">{ngo.name}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function DonationWorkbench({
  donors,
  ngos,
  donations: initialDonations,
  requests: initialRequests,
  initialMatchesByDonationId,
}: {
  donors: Donor[];
  ngos: NGO[];
  donations: Donation[];
  requests: AidRequest[];
  initialMatchesByDonationId: MatchesIndex;
}) {
  const router = useRouter();
  const [viewMode, setViewMode] = useState<ViewMode>("list");
  const [donations, setDonations] = useState(initialDonations);
  const [requests, setRequests] = useState(initialRequests);
  const [matchesByDonationId, setMatchesByDonationId] = useState<MatchesIndex>(initialMatchesByDonationId);
  const [selectedDonationId, setSelectedDonationId] = useState(
    initialDonations.find((donation) => donation.status === "available")?.id ?? initialDonations[0]?.id ?? "",
  );
  const [form, setForm] = useState<FormState>(() => defaultForm(donors));
  const [message, setMessage] = useState<string | null>(null);
  const [processingRequestId, setProcessingRequestId] = useState<string | null>(null);
  const [wasteRiskByDonationId, setWasteRiskByDonationId] = useState<Record<string, WasteRiskResponse>>({});
  const [expiryByDonationId, setExpiryByDonationId] = useState<Record<string, ExpiryPredictionResponse>>({});
  const [sortMode, setSortMode] = useState<SortMode>("ai_priority");
  const [isPending, startTransition] = useTransition();

  const selectedDonation = donations.find((donation) => donation.id === selectedDonationId);
  const selectedMatches = matchesByDonationId[selectedDonationId] ?? [];
  const selectedDonor = donors.find((donor) => donor.id === form.donor_id) ?? donors[0];
  const ngoLookup = Object.fromEntries(ngos.map((ngo) => [ngo.id, ngo]));
  const requestLookup = Object.fromEntries(requests.map((request) => [request.id, request]));
  const donorLookup = Object.fromEntries(donors.map((donor) => [donor.id, donor]));
  const safeUntilPreview = form.prepared_time ? computeSafeUntil(form) : null;
  const displayDonations = [...donations].sort((left, right) => {
    if (sortMode === "newest") {
      return new Date(right.created_at).getTime() - new Date(left.created_at).getTime();
    }

    const leftFreshness = expiryByDonationId[left.id];
    const rightFreshness = expiryByDonationId[right.id];
    const leftRisk = wasteRiskByDonationId[left.id]?.risk_score ?? 0;
    const rightRisk = wasteRiskByDonationId[right.id]?.risk_score ?? 0;
    const freshnessOrder = freshnessPriorityRank(leftFreshness) - freshnessPriorityRank(rightFreshness);
    if (freshnessOrder !== 0) {
      return freshnessOrder;
    }
    if (rightRisk !== leftRisk) {
      return rightRisk - leftRisk;
    }
    return new Date(right.created_at).getTime() - new Date(left.created_at).getTime();
  });
  const selectedLinkedRequests = selectedDonation
    ? requests.filter((request) => request.matched_donation_id === selectedDonation.id && request.status === "requested")
    : [];
  const selectedCandidateRequests = selectedMatches
    .map((match) => requestLookup[match.request_id])
    .filter((request): request is AidRequest => Boolean(request))
    .filter((request, index, collection) => collection.findIndex((item) => item.id === request.id) === index)
    .filter((request) => !["reserved", "fulfilled", "rejected", "cancelled", "expired"].includes(request.status))
    .filter((request) => !(request.status === "requested" && request.matched_donation_id === selectedDonation?.id));
  const selectedWasteRisk = selectedDonation ? wasteRiskByDonationId[selectedDonation.id] : undefined;
  const selectedExpiry = selectedDonation ? expiryByDonationId[selectedDonation.id] : undefined;

  useEffect(() => {
    if (!selectedDonationId || matchesByDonationId[selectedDonationId]) {
      return;
    }

    let cancelled = false;

    async function loadInitialMatches() {
      try {
        const matches = await fetchDonationMatchesFromApi(selectedDonationId);
        if (cancelled) {
          return;
        }
        setMatchesByDonationId((current) => ({ ...current, [selectedDonationId]: matches }));
      } catch {
        if (cancelled) {
          return;
        }
        setMatchesByDonationId((current) => ({ ...current, [selectedDonationId]: current[selectedDonationId] ?? [] }));
      }
    }

    void loadInitialMatches();

    return () => {
      cancelled = true;
    };
  }, [matchesByDonationId, selectedDonationId]);

  useEffect(() => {
    let cancelled = false;

    async function loadSignals() {
      const entries = await Promise.all(
        donations.map(async (donation) => {
          try {
            const [risk, expiry] = await Promise.all([getWasteRisk(donation.id), predictExpiryForDonation(donation)]);
            return [donation.id, { risk, expiry }] as const;
          } catch {
            return [donation.id, null] as const;
          }
        }),
      );

      if (cancelled) {
        return;
      }

      setWasteRiskByDonationId(
        Object.fromEntries(entries.filter((entry): entry is readonly [string, { risk: WasteRiskResponse; expiry: ExpiryPredictionResponse }] => entry[1] !== null).map(([id, value]) => [id, value.risk])),
      );
      setExpiryByDonationId(
        Object.fromEntries(entries.filter((entry): entry is readonly [string, { risk: WasteRiskResponse; expiry: ExpiryPredictionResponse }] => entry[1] !== null).map(([id, value]) => [id, value.expiry])),
      );
    }

    if (donations.length > 0) {
      void loadSignals();
    }

    return () => {
      cancelled = true;
    };
  }, [donations]);

  function updateForm(field: keyof FormState, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function applyImageAnalysis(analysis: FoodImageAnalysisResponse) {
    setForm((current) => ({
      ...current,
      category: analysis.food_category === "unknown" ? current.category : inferDomainCategoryFromFoodCategory(analysis.food_category),
      food_type: analysis.food_category === "unknown" ? current.food_type : inferFoodTypeFromImage(analysis),
      image_freshness_label: analysis.image_label,
      image_visual_label: analysis.visual_label,
      image_visual_confidence: analysis.visual_confidence.toFixed(0),
      title: current.title || analysis.food_type_guess,
      notes: `${current.notes}\nAI image insight: ${analysis.distribution_urgency}`.trim(),
    }));
    setMessage(
      analysis.category_uncertain
        ? `AI image analysis detected '${analysis.visual_label.replaceAll("_", " ")}' but left the food category unchanged because the category prediction is uncertain.`
        : `AI image recognition suggested ${analysis.food_type_guess.toLowerCase()} with visual state '${analysis.visual_label.replaceAll("_", " ")}' at ${analysis.visual_confidence.toFixed(0)}% confidence.`,
    );
  }

  async function refreshMatches(donationId: string) {
    try {
      const matches = await fetchDonationMatchesFromApi(donationId);
      setMatchesByDonationId((current) => ({ ...current, [donationId]: matches }));
    } catch {
      setMatchesByDonationId((current) => ({ ...current, [donationId]: current[donationId] ?? [] }));
    }
  }

  function createLocalDonation(payload: DonationCreatePayload): Donation {
    const safeUntil = payload.expires_at ?? computeSafeUntilFromPayload(payload);
    return {
      id: `local-${Date.now()}`,
      donor_id: payload.donor_id,
      title: payload.title,
      category: payload.category,
      food_type: payload.food_type,
      prepared_time: payload.prepared_time,
      storage_condition: payload.storage_condition,
      quantity: payload.quantity,
      unit: payload.unit,
      meals_estimate: payload.meals_estimate,
      safety_window_hours: payload.safety_window_hours,
      created_at: new Date().toISOString(),
      expires_at: safeUntil,
      pickup_start: payload.pickup_start,
      pickup_end: payload.pickup_end,
      status: "available",
      location: payload.location,
      shelf_life_hours: payload.shelf_life_hours ?? null,
      image_url: payload.image_url ?? null,
      image_freshness_label: payload.image_freshness_label ?? null,
      image_visual_label: payload.image_visual_label ?? null,
      image_visual_confidence: payload.image_visual_confidence ?? null,
      notes: payload.notes,
      request_id: null,
      reserved_for_request_id: null,
      picked_up_at: null,
      delivered_at: null,
    };
  }

  async function submitDonation() {
    if (!selectedDonor) {
      return;
    }

    const payload: DonationCreatePayload = {
      donor_id: form.donor_id,
      title: form.title,
      category: form.category,
      food_type: form.food_type,
      prepared_time: new Date(form.prepared_time).toISOString(),
      storage_condition: form.storage_condition,
      quantity: Number(form.quantity),
      unit: form.unit,
      meals_estimate: Number(form.meals_estimate),
      safety_window_hours: Number(form.safety_window_hours),
      shelf_life_hours: form.shelf_life_hours ? Number(form.shelf_life_hours) : undefined,
      image_freshness_label: form.image_freshness_label || undefined,
      image_visual_label: form.image_visual_label || undefined,
      image_visual_confidence: form.image_visual_confidence ? Number(form.image_visual_confidence) : undefined,
      pickup_start: new Date(form.pickup_start).toISOString(),
      pickup_end: new Date(form.pickup_end).toISOString(),
      location: selectedDonor.location,
      notes: form.notes,
    };

    try {
      const response = await fetch(
        `${API_BASE_URL}/donations`,
        createAuthorizedRequestInit({
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        }),
      );

      if (!response.ok) {
        throw new Error("Backend donation create failed");
      }

      const created = (await response.json()) as Donation;
      setDonations((current) => [created, ...current]);
      setMatchesByDonationId((current) => ({ ...current, [created.id]: [] }));
      setSelectedDonationId(created.id);
      setMessage("Donation created in the backend and queued for matching.");
      setForm(defaultForm(donors));
      await refreshMatches(created.id);
      router.refresh();
    } catch {
      const created = createLocalDonation(payload);
      setDonations((current) => [created, ...current]);
      setMatchesByDonationId((current) => ({ ...current, [created.id]: [] }));
      setSelectedDonationId(created.id);
      setMessage("Backend was unavailable, so the donation was added locally for UI review only.");
      setForm(defaultForm(donors));
    }
  }


  async function approveRequest(request: AidRequest, donation: Donation) {
    setProcessingRequestId(request.id);
    setMessage(null);

    const payload: RequestApprovalPayload = {
      donation_id: donation.id,
    };

    try {
      const response = await fetch(
        `${API_BASE_URL}/requests/${request.id}/approve`,
        createAuthorizedRequestInit({
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        }),
      );

      if (!response.ok) {
        throw new Error("Unable to approve the request right now.");
      }

      const approvedRequest = (await response.json()) as AidRequest;
      setRequests((current) => current.map((item) => (item.id === approvedRequest.id ? approvedRequest : item)));
      setDonations((current) =>
        current.map((item) =>
          item.id === donation.id
            ? {
                ...item,
                status: "reserved",
                request_id: approvedRequest.id,
                reserved_for_request_id: approvedRequest.id,
              }
            : item,
        ),
      );
      setMessage(`Approved ${approvedRequest.title} for ${donation.title}.`);
      await refreshMatches(donation.id);
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to approve the request right now.");
    } finally {
      setProcessingRequestId(null);
    }
  }

  async function rejectRequestDecision(request: AidRequest) {
    setProcessingRequestId(request.id);
    setMessage(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/requests/${request.id}/reject`,
        createAuthorizedRequestInit({
          method: "POST",
        }),
      );

      if (!response.ok) {
        throw new Error("Unable to reject the request right now.");
      }

      const rejectedRequest = (await response.json()) as AidRequest;
      setRequests((current) => current.map((item) => (item.id === rejectedRequest.id ? rejectedRequest : item)));
      setDonations((current) =>
        current.map((item) =>
          item.request_id === rejectedRequest.id || item.reserved_for_request_id === rejectedRequest.id
            ? {
                ...item,
                status: "available",
                request_id: null,
                reserved_for_request_id: null,
              }
            : item,
        ),
      );
      if (rejectedRequest.matched_donation_id) {
        await refreshMatches(rejectedRequest.matched_donation_id);
      }
      setMessage(`Rejected ${rejectedRequest.title}. The donation is available again.`);
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to reject the request right now.");
    } finally {
      setProcessingRequestId(null);
    }
  }

  return (
    <div className="space-y-8">
      <div className="grid gap-6 xl:grid-cols-[1.1fr_1.4fr]">
        <section className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-5">
            <p className="text-xs font-semibold uppercase tracking-[0.26em] text-slate-500">New donation</p>
            <h2 className="mt-2 text-2xl font-semibold text-slate-950">Create an outbound listing</h2>
            <p className="mt-2 text-sm text-slate-600">The form uses the donor pickup point as the dispatch location and immediately checks for ranked NGO matches.</p>
          </div>

          <div className="mb-5">
            <FoodImageAnalyzer onApply={applyImageAnalysis} />
          </div>

          <form
            className="grid gap-4 sm:grid-cols-2"
            onSubmit={(event) => {
              event.preventDefault();
              startTransition(() => {
                void submitDonation();
              });
            }}
          >
            <div className="space-y-2 sm:col-span-2">
              <span className="text-sm font-medium text-slate-700">Donor account</span>
              <div className="rounded-[1.4rem] border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                <span className="font-semibold text-slate-950">{selectedDonor?.name ?? "Donor profile unavailable"}</span>
                {selectedDonor ? ` · ${selectedDonor.location.area}` : ""}
              </div>
            </div>
            <label className="space-y-2 sm:col-span-2">
              <span className="text-sm font-medium text-slate-700">Listing title</span>
              <input
                value={form.title}
                onChange={(event) => updateForm("title", event.target.value)}
                placeholder="Ex: Packed lunch trays from finance summit"
                className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none"
                required
              />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-700">Category</span>
              <select
                value={form.category}
                onChange={(event) => updateForm("category", event.target.value)}
                className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none"
              >
                <option value="prepared_food">Prepared food</option>
                <option value="dry_rations">Dry rations</option>
                <option value="bakery">Bakery</option>
              </select>
            </label>
            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-700">Food type</span>
              <select
                value={form.food_type}
                onChange={(event) => updateForm("food_type", event.target.value)}
                className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none"
              >
                <option value="biryani">Biryani</option>
                <option value="fruit">Fruit</option>
                <option value="haleem">Haleem</option>
                <option value="curry">Curry</option>
                <option value="rice">Rice</option>
                <option value="chicken_curry">Chicken curry</option>
                <option value="naan">Naan</option>
                <option value="bread_or_bakery">Bread / bakery</option>
                <option value="dessert">Dessert</option>
                <option value="fried_rice">Fried rice</option>
                <option value="kebab">Kebab</option>
                <option value="double_ka_meetha">Double ka meetha</option>
                <option value="dry_rations">Dry rations</option>
              </select>
            </label>
            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-700">Storage condition</span>
              <select
                value={form.storage_condition}
                onChange={(event) => updateForm("storage_condition", event.target.value)}
                className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none"
              >
                <option value="ambient">Ambient</option>
                <option value="insulated">Insulated</option>
                <option value="chilled">Chilled</option>
                <option value="frozen">Frozen</option>
              </select>
            </label>
            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-700">Prepared at</span>
              <input
                type="datetime-local"
                value={form.prepared_time}
                onChange={(event) => updateForm("prepared_time", event.target.value)}
                className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none"
                required
              />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-700">Shelf life override (hours)</span>
              <input
                type="number"
                min="0.5"
                step="0.25"
                value={form.shelf_life_hours}
                onChange={(event) => updateForm("shelf_life_hours", event.target.value)}
                placeholder={`${inferShelfLifeHours(form.food_type, form.storage_condition, "")} inferred`}
                className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none"
              />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-700">Unit</span>
              <input
                value={form.unit}
                onChange={(event) => updateForm("unit", event.target.value)}
                className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none"
                required
              />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-700">Quantity</span>
              <input
                type="number"
                min="1"
                value={form.quantity}
                onChange={(event) => updateForm("quantity", event.target.value)}
                className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none"
                required
              />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-700">Meals estimate</span>
              <input
                type="number"
                min="0"
                value={form.meals_estimate}
                onChange={(event) => updateForm("meals_estimate", event.target.value)}
                className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none"
                required
              />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-700">Safety window (hours)</span>
              <input
                type="number"
                min="0"
                value={form.safety_window_hours}
                onChange={(event) => updateForm("safety_window_hours", event.target.value)}
                className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none"
                required
              />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-700">Pickup start</span>
              <input
                type="datetime-local"
                value={form.pickup_start}
                onChange={(event) => updateForm("pickup_start", event.target.value)}
                className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none"
                required
              />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-700">Pickup end</span>
              <input
                type="datetime-local"
                value={form.pickup_end}
                onChange={(event) => updateForm("pickup_end", event.target.value)}
                className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none"
                required
              />
            </label>
            <div className="sm:col-span-2 rounded-[1.4rem] border border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-700">
              <div className="text-sm font-medium text-slate-700">AI-derived safe window</div>
              <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-slate-600">
                <span>Prepared at <span className="font-semibold text-slate-950">{form.prepared_time ? formatDateTime(new Date(form.prepared_time).toISOString()) : "-"}</span></span>
                <span>Safe until <span className="font-semibold text-slate-950">{safeUntilPreview ? formatDateTime(safeUntilPreview) : "-"}</span></span>
                <AIBadge label="Time-driven freshness" tone="sky" detail={`${inferShelfLifeHours(form.food_type, form.storage_condition, form.shelf_life_hours)}h shelf life`} />
                {form.image_freshness_label ? <AIBadge label={`Image ${form.image_freshness_label}`} tone={form.image_freshness_label === "spoiled" ? "rose" : form.image_freshness_label === "medium" ? "amber" : "emerald"} /> : null}
                {form.image_visual_label ? <AIBadge label={`Visual ${form.image_visual_label.replaceAll("_", " ")}`} tone="slate" detail={form.image_visual_confidence ? `${form.image_visual_confidence}%` : undefined} /> : null}
              </div>
            </div>
            <label className="space-y-2 sm:col-span-2">
              <span className="text-sm font-medium text-slate-700">Operational notes</span>
              <textarea
                rows={4}
                value={form.notes}
                onChange={(event) => updateForm("notes", event.target.value)}
                className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none"
              />
            </label>
            <div className="sm:col-span-2 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="text-sm text-slate-600">
                Pickup point: <span className="font-medium text-slate-900">{selectedDonor?.location.address}</span>
              </div>
              <button
                type="submit"
                className="rounded-full bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
                disabled={isPending}
              >
                {isPending ? "Saving..." : "Create donation"}
              </button>
            </div>
          </form>
          {message ? <p className="mt-4 text-sm font-medium text-sky-700">{message}</p> : null}
        </section>

        <section className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.26em] text-slate-500">Request review</p>
              <h2 className="mt-2 text-2xl font-semibold text-slate-950">Approve or reject NGO demand</h2>
              <p className="mt-2 text-sm text-slate-600">Select a donation to review the NGO requests attached to it and accept meal demand against that listing.</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex items-center gap-2 rounded-full bg-slate-100 p-1">
                <button
                  type="button"
                  onClick={() => setSortMode("ai_priority")}
                  className={`rounded-full px-4 py-2 text-sm font-medium ${sortMode === "ai_priority" ? "bg-white text-slate-950 shadow" : "text-slate-600"}`}
                >
                  AI priority
                </button>
                <button
                  type="button"
                  onClick={() => setSortMode("newest")}
                  className={`rounded-full px-4 py-2 text-sm font-medium ${sortMode === "newest" ? "bg-white text-slate-950 shadow" : "text-slate-600"}`}
                >
                  Newest
                </button>
              </div>
              <div className="flex items-center gap-2 rounded-full bg-slate-100 p-1">
                <button
                  type="button"
                  onClick={() => setViewMode("list")}
                  className={`rounded-full px-4 py-2 text-sm font-medium ${viewMode === "list" ? "bg-white text-slate-950 shadow" : "text-slate-600"}`}
                >
                  List
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode("map")}
                  className={`rounded-full px-4 py-2 text-sm font-medium ${viewMode === "map" ? "bg-white text-slate-950 shadow" : "text-slate-600"}`}
                >
                  Map
                </button>
              </div>
            </div>
          </div>

          {selectedDonation ? (
            <div className="mb-5 rounded-[1.75rem] border border-slate-200 bg-slate-50/80 p-5">
              <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-xl font-semibold text-slate-950">{selectedDonation.title}</h3>
                    <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ring-1 ${tone(selectedDonation.status)}`}>
                      {formatStatusLabel(selectedDonation.status)}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-slate-600">
                    {donorLookup[selectedDonation.donor_id]?.name} · {selectedDonation.location.area} · {selectedDonation.quantity} {selectedDonation.unit}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {selectedWasteRisk ? (
                      <AIBadge
                        label={`Waste risk ${selectedWasteRisk.risk_label}`}
                        tone={selectedWasteRisk.risk_label === "high" ? "rose" : selectedWasteRisk.risk_label === "medium" ? "amber" : "emerald"}
                        detail={`${selectedWasteRisk.risk_score.toFixed(0)}/100`}
                      />
                    ) : null}
                    {selectedExpiry ? (
                      <AIBadge
                        label={selectedExpiry.final_status === "unsafe" ? "Unsafe" : selectedExpiry.final_status === "urgent" ? "Urgent" : "Safe"}
                        tone={selectedExpiry.final_status === "unsafe" ? "rose" : selectedExpiry.final_status === "urgent" ? "amber" : "sky"}
                        detail={`${selectedExpiry.time_left_hours}h left`}
                      />
                    ) : null}
                  </div>
                </div>
                <div className="flex flex-col items-start gap-3 text-sm text-slate-600 md:items-end">
                  <div>
                    <div>Prepared: {formatDateTime(selectedDonation.prepared_time)}</div>
                    <div>Pickup: {formatDateTime(selectedDonation.pickup_start)}</div>
                    <div>Safe until: {selectedExpiry ? formatDateTime(selectedExpiry.safe_until) : formatDateTime(selectedDonation.expires_at)}</div>
                  </div>
                  <p className="max-w-xs text-sm text-slate-600 md:text-right">
                    {selectedLinkedRequests.length > 0
                      ? `${selectedLinkedRequests.length} NGO request${selectedLinkedRequests.length > 1 ? "s" : ""} waiting for your decision.`
                      : selectedDonation.status === "reserved"
                        ? "This donation is already committed to an NGO request."
                        : "This donation is available for NGO review and approval."}
                  </p>
                </div>
              </div>
            </div>
          ) : null}

          {viewMode === "map" ? (
            <MapCanvas
              donations={donations}
              ngos={ngos}
              selectedDonation={selectedDonation}
              matches={selectedMatches}
              onSelect={setSelectedDonationId}
            />
          ) : (
            <div className="grid gap-3">
              {displayDonations.map((donation) => {
                const donor = donorLookup[donation.donor_id];
                const selected = donation.id === selectedDonationId;
                const donationRisk = wasteRiskByDonationId[donation.id];
                const donationExpiry = expiryByDonationId[donation.id];

                return (
                  <div
                    key={donation.id}
                    className={`rounded-[1.6rem] border p-4 text-left transition ${
                      selected
                        ? "border-slate-950 bg-slate-950 text-white shadow-sm"
                        : "border-slate-200 bg-slate-50/75 text-slate-900 hover:border-slate-300 hover:bg-white"
                    }`}
                  >
                    <button type="button" onClick={() => setSelectedDonationId(donation.id)} className="w-full text-left">
                      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-base font-semibold">{donation.title}</span>
                            <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ring-1 ${tone(donation.status)}`}>
                              {formatStatusLabel(donation.status)}
                            </span>
                            {donationExpiry ? (
                              <AIBadge
                                label={donationExpiry.final_status === "unsafe" ? "Unsafe" : donationExpiry.final_status === "urgent" ? "Expiring Soon" : "Safe"}
                                tone={donationExpiry.final_status === "unsafe" ? "rose" : donationExpiry.final_status === "urgent" ? "amber" : "sky"}
                                detail={`${donationExpiry.time_left_hours}h`}
                              />
                            ) : null}
                            {donationRisk ? (
                              <AIBadge
                                label={donationRisk.risk_label === "high" ? "High Waste Risk" : donationRisk.risk_label === "medium" ? "Watch Closely" : "Low Waste Risk"}
                                tone={donationRisk.risk_label === "high" ? "rose" : donationRisk.risk_label === "medium" ? "amber" : "emerald"}
                              />
                            ) : null}
                          </div>
                          <p className={`mt-2 text-sm ${selected ? "text-slate-200" : "text-slate-600"}`}>
                            {donor?.name} · {donation.location.area} · {donation.quantity} {donation.unit}
                          </p>
                        </div>
                        <div className={`text-sm ${selected ? "text-slate-200" : "text-slate-600"}`}>
                          <div>Prepared {formatDateTime(donation.prepared_time)}</div>
                          <div>Safe until {formatDateTime(donationExpiry?.safe_until ?? donation.expires_at)}</div>
                        </div>
                      </div>
                    </button>
                    <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                      <p className={`text-sm ${selected ? "text-slate-200" : "text-slate-600"}`}>
                        {donation.request_id
                          ? `Current request: ${requestLookup[donation.request_id]?.title ?? donation.request_id}`
                          : "Awaiting NGO request or donor approval."}
                      </p>
                      <span className={`rounded-full px-4 py-2 text-sm font-semibold ${selected ? "bg-white text-slate-950" : "bg-slate-100 text-slate-700"}`}>
                        {donation.status === "requested" ? "Pending approval" : donation.status === "reserved" ? "Approved" : "Open listing"}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </div>

      <DonationIntelligencePanel donation={selectedDonation} />

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.9fr]">
        <section className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-5">
            <p className="text-xs font-semibold uppercase tracking-[0.26em] text-slate-500">Donation list</p>
            <h2 className="mt-2 text-2xl font-semibold text-slate-950">Operational queue</h2>
            <p className="mt-2 text-sm text-slate-600">Selected items surface their current request reservation and timing details.</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <AIBadge label="High Priority" tone="rose" />
              <AIBadge label="Safe to Schedule" tone="sky" />
              <AIBadge label="Unsafe / Do Not Distribute" tone="rose" />
            </div>
          </div>
            <div className="grid gap-3">
              {displayDonations.map((donation) => {
                const request = donation.request_id ? requestLookup[donation.request_id] : null;
                const donationRisk = wasteRiskByDonationId[donation.id];
                const donationExpiry = expiryByDonationId[donation.id];
                return (
                  <div key={`queue-${donation.id}`} className="rounded-[1.5rem] border border-slate-200 bg-white p-4">
                  <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-lg font-semibold text-slate-950">{donation.title}</h3>
                        <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ring-1 ${tone(donation.status)}`}>
                          {formatStatusLabel(donation.status)}
                        </span>
                        {donationRisk ? (
                          <AIBadge
                            label={donationRisk.risk_label === "high" ? "Prioritize now" : donationRisk.risk_label === "medium" ? "Medium urgency" : "Stable"}
                            tone={donationRisk.risk_label === "high" ? "rose" : donationRisk.risk_label === "medium" ? "amber" : "emerald"}
                          />
                        ) : null}
                        {donationExpiry ? (
                          <AIBadge
                            label={donationExpiry.final_status === "unsafe" ? "Unsafe" : donationExpiry.final_status === "urgent" ? "Urgent" : "Safe to schedule"}
                            tone={donationExpiry.final_status === "unsafe" ? "rose" : donationExpiry.final_status === "urgent" ? "amber" : "sky"}
                            detail={`${donationExpiry.time_left_hours}h`}
                          />
                        ) : null}
                      </div>
                      <p className="mt-2 text-sm text-slate-600">{donation.notes || "No extra operational notes."}</p>
                      <p className="mt-2 text-sm text-slate-500">Prepared {formatDateTime(donation.prepared_time)} · Safe until {formatDateTime(donationExpiry?.safe_until ?? donation.expires_at)}</p>
                    </div>
                    <div className="text-sm text-slate-600">
                      <div>{donation.quantity} {donation.unit}</div>
                      <div>{donation.location.area}</div>
                    </div>
                  </div>
                  <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                    <p className="text-sm text-slate-600">
                      {request ? `${ngoLookup[request.ngo_id]?.name ?? "NGO"} is attached to this listing.` : "No NGO request is attached to this listing yet."}
                    </p>
                    <span className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700">
                      {donation.status === "requested" ? "Pending approval" : donation.status === "reserved" ? "Approved" : "Available"}
                    </span>
                  </div>
                  {request ? (
                    <div className="mt-4 rounded-2xl bg-slate-50 p-3 text-sm text-slate-700">
                      <span className="font-semibold text-slate-950">{request.title}</span> · {ngoLookup[request.ngo_id]?.name}
                      {request.meal_slot ? ` · ${request.meal_slot}` : ""}
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        </section>

        <section className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-5">
            <p className="text-xs font-semibold uppercase tracking-[0.26em] text-slate-500">Decision panel</p>
            <h2 className="mt-2 text-2xl font-semibold text-slate-950">Pending NGO requests and ranked demand</h2>
          </div>
          <div className="space-y-4">
            {selectedLinkedRequests.length > 0 ? (
              <div className="space-y-3">
                {selectedLinkedRequests.map((request) => (
                  <div key={`pending-${request.id}`} className="rounded-[1.6rem] border border-amber-200 bg-amber-50/70 p-4">
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="text-lg font-semibold text-slate-950">{request.title}</h3>
                          <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ring-1 ${tone(request.status)}`}>
                            {formatStatusLabel(request.status)}
                          </span>
                        </div>
                        <p className="mt-2 text-sm text-slate-600">{ngoLookup[request.ngo_id]?.name} · {request.quantity_needed} {request.unit} · Needed {formatDateTime(request.needed_by)}</p>
                        {request.meal_slot ? <p className="mt-2 text-sm text-slate-600">Meal slot: <span className="font-semibold capitalize text-slate-950">{request.meal_slot}</span></p> : null}
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => {
                            if (selectedDonation) {
                              void approveRequest(request, selectedDonation);
                            }
                          }}
                          disabled={!selectedDonation || processingRequestId === request.id}
                          className="rounded-full bg-slate-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-600"
                        >
                          {processingRequestId === request.id ? "Saving..." : "Approve request"}
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            void rejectRequestDecision(request);
                          }}
                          disabled={processingRequestId === request.id}
                          className="rounded-full border border-rose-200 bg-white px-4 py-2 text-sm font-semibold text-rose-700 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:text-rose-300"
                        >
                          Reject request
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : null}

            {selectedCandidateRequests.length === 0 ? (
              <div className="rounded-[1.6rem] border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-600">
                No additional NGO meal requests are waiting to be matched against the selected donation.
              </div>
            ) : (
              selectedCandidateRequests.map((request) => {
                const match = selectedMatches.find((item) => item.request_id === request.id);
                if (!match) {
                  return null;
                }

                return (
                  <div key={match.request_id} className="rounded-[1.6rem] border border-slate-200 bg-white p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <div className="text-lg font-semibold text-slate-950">{match.ngo_name}</div>
                          <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ring-1 ${tone(request.status)}`}>
                            {formatStatusLabel(request.status)}
                          </span>
                        </div>
                        <p className="text-sm text-slate-600">{match.request_title}</p>
                        {request.meal_slot ? <p className="mt-2 text-sm text-slate-600">Meal slot: <span className="font-semibold capitalize text-slate-950">{request.meal_slot}</span></p> : null}
                      </div>
                      <div className="rounded-2xl bg-slate-950 px-3 py-2 text-sm font-semibold text-white">{match.total_score.toFixed(1)}</div>
                    </div>
                    <p className="mt-3 text-sm text-slate-600">{match.explanation}</p>
                    <div className="mt-4 grid gap-3">
                      <FactorBar label="Distance" value={match.factor_scores.distance} />
                      <FactorBar label="Expiry urgency" value={match.factor_scores.expiry_urgency} />
                      <FactorBar label="Safety window" value={match.factor_scores.safety_window} />
                      <FactorBar label="Capacity" value={match.factor_scores.capacity} />
                      <FactorBar label="Demand" value={match.factor_scores.demand} />
                      <FactorBar label="Reliability" value={match.factor_scores.reliability} />
                    </div>
                    <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-slate-500">
                      <span>Distance: {match.distance_km.toFixed(1)} km</span>
                      <button
                        type="button"
                        onClick={() => {
                          if (selectedDonation) {
                            void approveRequest(request, selectedDonation);
                          }
                        }}
                        disabled={!selectedDonation || processingRequestId === request.id || !["available", "requested"].includes(selectedDonation?.status ?? "")}
                        className="rounded-full bg-slate-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-600"
                      >
                        {processingRequestId === request.id ? "Saving..." : "Approve with this donation"}
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
