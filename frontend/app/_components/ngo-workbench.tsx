"use client";

import { useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { SectionCard } from "@/app/_components/section-card";
import { StatCard } from "@/app/_components/stat-card";
import { StatusPill } from "@/app/_components/status-pill";
import { createAuthorizedRequestInit } from "@/app/_lib/auth-client";
import { API_BASE_URL } from "@/app/_lib/api-config";
import { formatDateTime } from "@/app/_lib/format";
import type { AidRequest, Donation, DonationRequestPayload, MealRequestCreatePayload, MealSlot, NGO } from "@/app/_lib/types";

type FormState = {
  ngo_id: string;
  meal_slot: MealSlot;
  quantity_needed: string;
  needed_by: string;
  max_distance_km: string;
  notes: string;
};

function toDatetimeLocal(value: Date) {
  return new Date(value.getTime() - value.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
}

function defaultForm(ngos: NGO[]): FormState {
  return {
    ngo_id: ngos[0]?.id ?? "",
    meal_slot: "breakfast",
    quantity_needed: "60",
    needed_by: toDatetimeLocal(new Date(Date.now() + 4 * 60 * 60 * 1000)),
    max_distance_km: "12",
    notes: "Prepared meal request for an upcoming service window.",
  };
}

function priorityForMealSlot(mealSlot: MealSlot): number {
  if (mealSlot === "breakfast") {
    return 5;
  }
  if (mealSlot === "lunch") {
    return 4;
  }
  return 3;
}

function mealTitle(mealSlot: MealSlot, quantityNeeded: number): string {
  const label = mealSlot[0].toUpperCase() + mealSlot.slice(1);
  return `${label} meals for ${quantityNeeded} people`;
}

export function NgoWorkbench({ ngos, requests: initialRequests, donations: initialDonations }: { ngos: NGO[]; requests: AidRequest[]; donations: Donation[] }) {
  const router = useRouter();
  const [requests, setRequests] = useState(initialRequests);
  const [donations, setDonations] = useState(initialDonations);
  const [form, setForm] = useState<FormState>(() => defaultForm(ngos));
  const [message, setMessage] = useState<string | null>(null);
  const [requestingDonationId, setRequestingDonationId] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const donationLookup = useMemo(() => Object.fromEntries(donations.map((donation) => [donation.id, donation])), [donations]);
  const selectedNgo = ngos.find((ngo) => ngo.id === form.ngo_id) ?? ngos[0];
  const availableDonations = donations.filter((donation) => donation.status === "available");
  const ngoRequests = requests
    .filter((request) => request.ngo_id === form.ngo_id)
    .sort((left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime());

  function updateForm(field: keyof FormState, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submitMealRequest() {
    if (!selectedNgo) {
      return;
    }

    const quantityNeeded = Number(form.quantity_needed);
    const payload: MealRequestCreatePayload = {
      ngo_id: form.ngo_id,
      title: mealTitle(form.meal_slot, quantityNeeded),
      category: "prepared_food",
      quantity_needed: quantityNeeded,
      unit: "meal_boxes",
      people_served: quantityNeeded,
      priority: priorityForMealSlot(form.meal_slot),
      needed_by: new Date(form.needed_by).toISOString(),
      max_distance_km: Number(form.max_distance_km),
      location: selectedNgo.location,
      meal_slot: form.meal_slot,
      notes: form.notes,
    };

    setMessage(null);

    const response = await fetch(
      `${API_BASE_URL}/requests`,
      createAuthorizedRequestInit({
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      }),
    );

    if (!response.ok) {
      throw new Error("Unable to create the meal request right now.");
    }

    const created = (await response.json()) as AidRequest;
    setRequests((current) => [created, ...current]);
    setForm((current) => ({ ...defaultForm(ngos), ngo_id: current.ngo_id }));
    setMessage(`${selectedNgo.name} opened a ${form.meal_slot} request for ${quantityNeeded} meal boxes.`);
    router.refresh();
  }

  async function requestListedDonation(donation: Donation) {
    if (!selectedNgo) {
      return;
    }

    setRequestingDonationId(donation.id);
    setMessage(null);

    const payload: DonationRequestPayload = {
      donation_id: donation.id,
      ngo_id: selectedNgo.id,
    };

    const response = await fetch(
      `${API_BASE_URL}/requests`,
      createAuthorizedRequestInit({
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      }),
    );

    if (!response.ok) {
      setRequestingDonationId(null);
      throw new Error(`Unable to request ${donation.title} right now.`);
    }

    const created = (await response.json()) as AidRequest;
    setRequests((current) => [created, ...current]);
    setDonations((current) =>
      current.map((item) =>
        item.id === donation.id
          ? {
              ...item,
              status: "requested",
              request_id: created.id,
            }
          : item,
      ),
    );
    setMessage(`${selectedNgo.name} sent a request for ${donation.title}. Waiting for donor approval.`);
    setRequestingDonationId(null);
    router.refresh();
  }

  return (
    <div className="space-y-8">
      <section className="grid gap-4 md:grid-cols-3">
        <StatCard eyebrow="NGO account" value={ngos.length.toString()} detail="Authenticated NGO profile currently in scope." />
        <StatCard eyebrow="Active requests" value={requests.filter((request) => ["open", "requested", "matched", "reserved"].includes(request.status)).length.toString()} detail="Demand waiting for matching, approval, or delivery." />
        <StatCard eyebrow="Available donations" value={availableDonations.length.toString()} detail="Live donor listings that can still be requested." />
      </section>

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <SectionCard title="NGO request desk" description="Open a breakfast, lunch, or dinner requirement from the NGO side.">
          <form
            className="grid gap-4 md:grid-cols-2"
            onSubmit={(event) => {
              event.preventDefault();
              startTransition(() => {
                void submitMealRequest().catch((error: unknown) => {
                  setMessage(error instanceof Error ? error.message : "Unable to create the request right now.");
                });
              });
            }}
          >
            <div className="space-y-2 md:col-span-2">
              <span className="text-sm font-medium text-slate-700">NGO account</span>
              <div className="rounded-[1.4rem] border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                <span className="font-semibold text-slate-950">{selectedNgo?.name ?? "NGO profile unavailable"}</span>
                {selectedNgo ? ` · ${selectedNgo.location.area}` : ""}
              </div>
            </div>
            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-700">Meal slot</span>
              <select value={form.meal_slot} onChange={(event) => updateForm("meal_slot", event.target.value)} className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none">
                <option value="breakfast">Breakfast</option>
                <option value="lunch">Lunch</option>
                <option value="dinner">Dinner</option>
              </select>
            </label>
            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-700">Meal amount</span>
              <input type="number" min="1" value={form.quantity_needed} onChange={(event) => updateForm("quantity_needed", event.target.value)} className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none" required />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-700">Needed by</span>
              <input type="datetime-local" value={form.needed_by} onChange={(event) => updateForm("needed_by", event.target.value)} className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none" required />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-700">Max distance (km)</span>
              <input type="number" min="1" value={form.max_distance_km} onChange={(event) => updateForm("max_distance_km", event.target.value)} className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none" required />
            </label>
            <label className="space-y-2 md:col-span-2">
              <span className="text-sm font-medium text-slate-700">Operational notes</span>
              <textarea rows={4} value={form.notes} onChange={(event) => updateForm("notes", event.target.value)} className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none" />
            </label>
            <div className="md:col-span-2 flex items-center justify-between gap-3">
              <p className="text-sm text-slate-600">The request opens immediately and becomes available to donors for approval.</p>
              <button type="submit" className="rounded-full bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400" disabled={isPending}>
                {isPending ? "Saving..." : "Open meal request"}
              </button>
            </div>
          </form>
          {message ? <p className="mt-4 text-sm font-medium text-sky-700">{message}</p> : null}
        </SectionCard>

        <SectionCard title="Available donor listings" description="Request a live donation listing and wait for donor approval.">
          <div className="grid gap-3">
            {availableDonations.length === 0 ? (
              <div className="rounded-[1.6rem] border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-600">No live donation listings are available right now.</div>
            ) : (
              availableDonations.map((donation) => (
                <div key={donation.id} className="rounded-[1.5rem] border border-slate-200 bg-white p-4">
                  <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-lg font-semibold text-slate-950">{donation.title}</h3>
                        <StatusPill status={donation.status} />
                      </div>
                      <p className="mt-2 text-sm text-slate-600">{donation.location.area} · {donation.quantity} {donation.unit} · Expires {formatDateTime(donation.expires_at)}</p>
                      <p className="mt-2 text-sm text-slate-600">{donation.notes || "No extra operational notes."}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        startTransition(() => {
                          void requestListedDonation(donation).catch((error: unknown) => {
                            setMessage(error instanceof Error ? error.message : "Unable to request that donation right now.");
                          });
                        });
                      }}
                      disabled={isPending || requestingDonationId === donation.id || !selectedNgo}
                      className="rounded-full bg-slate-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-600"
                    >
                      {requestingDonationId === donation.id ? "Requesting..." : "Request this donation"}
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </SectionCard>
      </div>

      <SectionCard title="NGO dashboard" description="Capacity, focus area, and request visibility by partner.">
        <div className="mb-5 rounded-[1.6rem] border border-slate-200 bg-slate-50 p-4">
          <p className="text-sm text-slate-600">Active request desk: <span className="font-semibold text-slate-950">{selectedNgo?.name ?? "Not selected"}</span></p>
        </div>
        <div className="grid gap-4 xl:grid-cols-3">
          {ngos.map((ngo) => {
            const ngoSpecificRequests = requests
              .filter((request) => request.ngo_id === ngo.id)
              .sort((left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime());
            const utilization = Math.round((ngo.current_load / Math.max(ngo.max_daily_capacity, 1)) * 100);

            return (
              <div key={ngo.id} className="rounded-[1.7rem] border border-slate-200 bg-white p-5">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="text-xl font-semibold text-slate-950">{ngo.name}</h3>
                    <p className="mt-1 text-sm text-slate-600">{ngo.contact_name} · {ngo.location.area}</p>
                  </div>
                  <div className="rounded-2xl bg-indigo-50 px-3 py-2 text-sm font-semibold text-indigo-700">{ngo.reliability}%</div>
                </div>
                <div className="mt-5 rounded-[1.4rem] bg-slate-50 p-4">
                  <div className="flex items-center justify-between text-sm text-slate-600">
                    <span>Capacity utilization</span>
                    <span className="font-semibold text-slate-950">{utilization}%</span>
                  </div>
                  <div className="mt-3 h-2 rounded-full bg-slate-200">
                    <div className="h-2 rounded-full bg-gradient-to-r from-indigo-500 to-sky-500" style={{ width: `${Math.min(utilization, 100)}%` }} />
                  </div>
                  <p className="mt-3 text-sm text-slate-600">{ngo.current_load} / {ngo.max_daily_capacity} units scheduled today</p>
                </div>
                <div className="mt-4 flex flex-wrap gap-2 text-xs text-slate-600">
                  {ngo.focus_areas.map((area) => (
                    <span key={area} className="rounded-full bg-slate-100 px-3 py-1 font-medium">
                      {area.replaceAll("_", " ")}
                    </span>
                  ))}
                </div>
                <div className="mt-5 space-y-3">
                  {ngoSpecificRequests.map((request) => (
                    <div key={request.id} className="rounded-2xl border border-slate-200 bg-slate-50/80 p-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium text-slate-950">{request.title}</span>
                        <StatusPill status={request.status} />
                      </div>
                      <p className="mt-2 text-sm text-slate-600">Priority {request.priority} · {request.people_served} people · {request.max_distance_km} km</p>
                      {request.meal_slot ? <p className="mt-2 text-sm text-slate-600">Meal slot: <span className="font-semibold text-slate-950 capitalize">{request.meal_slot}</span></p> : null}
                      {request.matched_donation_id ? (
                        <p className="mt-2 text-sm text-sky-700">
                          Linked donation: <span className="font-semibold">{donationLookup[request.matched_donation_id]?.title ?? request.matched_donation_id}</span>
                        </p>
                      ) : null}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </SectionCard>
    </div>
  );
}
