"use client";

import { useEffect, useState } from "react";

import { AIBadge } from "@/app/_components/ai-badge";
import { SectionCard } from "@/app/_components/section-card";
import { getAIMatch, getWasteRisk, optimizeRoute, predictExpiryForDonation } from "@/app/_lib/ai";
import { formatDateTime } from "@/app/_lib/format";
import type { AIMatchResponse, Donation, ExpiryPredictionResponse, RouteOptimizationResponse, WasteRiskResponse } from "@/app/_lib/types";

export function DonationIntelligencePanel({ donation }: { donation: Donation | undefined }) {
  const [match, setMatch] = useState<AIMatchResponse | null>(null);
  const [expiry, setExpiry] = useState<ExpiryPredictionResponse | null>(null);
  const [route, setRoute] = useState<RouteOptimizationResponse | null>(null);
  const [risk, setRisk] = useState<WasteRiskResponse | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!donation) {
        setMatch(null);
        setExpiry(null);
        setRoute(null);
        setRisk(null);
        return;
      }

      try {
        const [matchResult, expiryResult, routeResult, riskResult] = await Promise.all([
          getAIMatch(donation.id),
          predictExpiryForDonation(donation),
          optimizeRoute({ donation_id: donation.id }),
          getWasteRisk(donation.id),
        ]);
        if (!cancelled) {
          setMatch(matchResult);
          setExpiry(expiryResult);
          setRoute(routeResult);
          setRisk(riskResult);
        }
      } catch {
        if (!cancelled) {
          setMatch(null);
          setExpiry(null);
          setRoute(null);
          setRisk(null);
        }
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, [donation]);

  return (
    <SectionCard title="AI recommendation stack" description="Smart matching, route optimization, safety prediction, and waste-risk signals for the selected donation.">
      {donation ? (
        <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
          <div className="space-y-4">
            <div className="rounded-[1.6rem] bg-slate-950 p-5 text-white">
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-sky-300">Best NGO match</p>
              <h3 className="mt-3 text-2xl font-semibold">{match?.best_match?.ngo_name ?? "Matching..."}</h3>
              <p className="mt-2 text-sm text-slate-300">{match?.best_match ? `${match.best_match.fit_percentage.toFixed(1)}% fit and ${match.best_match.confidence_percentage.toFixed(1)}% confidence for ${match.best_match.request_title}.` : "Scoring the strongest receiving partner based on distance, urgency, capacity, and demand."}</p>
              {match?.best_match ? (
                <div className="mt-4 flex flex-wrap gap-2">
                  <AIBadge label={match.best_match.feasible ? "Feasible" : "Not feasible"} tone={match.best_match.feasible ? "emerald" : "rose"} detail={`${match.best_match.eta_minutes} min ETA`} />
                  <AIBadge label={`Final ${match.best_match.final_status}`} tone={match.best_match.final_status === "unsafe" ? "rose" : match.best_match.final_status === "urgent" ? "amber" : "sky"} detail={`Time ${match.best_match.time_based_status}`} />
                  {match.best_match.reasons.map((reason) => <AIBadge key={reason} label={reason} tone="sky" />)}
                </div>
              ) : null}
            </div>

            <div className="rounded-[1.6rem] border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Waste risk</p>
              <div className="mt-3 flex flex-wrap items-center gap-3">
                {risk ? <AIBadge label={`${risk.risk_label.toUpperCase()} risk`} tone={risk.risk_label === "high" ? "rose" : risk.risk_label === "medium" ? "amber" : "emerald"} detail={`${risk.risk_score.toFixed(0)}/100`} /> : null}
                {risk ? <AIBadge label="Best match" tone="violet" detail={`${risk.best_match_fit.toFixed(1)}%`} /> : null}
              </div>
              <p className="mt-3 text-sm text-slate-600">{risk?.recommended_action ?? "Assessing rescue urgency and likely waste exposure for this donation."}</p>
              <div className="mt-4 space-y-2">
                {risk?.top_reasons.map((reason) => (
                  <p key={reason} className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-700 ring-1 ring-slate-200">
                    {reason}
                  </p>
                ))}
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div className="rounded-[1.6rem] border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Food safety prediction</p>
              <div className="mt-3 flex flex-wrap items-center gap-3">
                {expiry ? <AIBadge label={`Final ${expiry.final_status}`} tone={expiry.final_status === "unsafe" ? "rose" : expiry.final_status === "urgent" ? "amber" : "emerald"} detail={`${expiry.time_left_hours}h left`} /> : null}
                {expiry ? <AIBadge label={`Time ${expiry.time_based_status}`} tone={expiry.time_based_status === "unsafe" ? "rose" : expiry.time_based_status === "urgent" ? "amber" : "sky"} /> : null}
                {expiry?.visual_label ? <AIBadge label={`Visual ${expiry.visual_label.replaceAll("_", " ")}`} tone={expiry.final_status === "unsafe" ? "rose" : expiry.final_status === "urgent" ? "amber" : "slate"} detail={expiry.visual_confidence ? `${expiry.visual_confidence.toFixed(0)}%` : undefined} /> : null}
              </div>
              <p className="mt-3 text-sm text-slate-600">{expiry ? `Category: ${expiry.food_category.replaceAll("_", " ")} · Prepared at ${formatDateTime(donation.prepared_time)} · Safe until ${formatDateTime(expiry.safe_until)}.` : "Predicting the remaining safe window from storage, packaging, and category assumptions."}</p>
              <p className="mt-2 text-sm text-slate-600">{expiry ? `Time elapsed: ${expiry.time_elapsed_hours}h · Time left: ${expiry.time_left_hours}h · Urgency: ${expiry.urgency_status.replaceAll("_", " ")}` : null}</p>
              <p className="mt-3 text-sm text-slate-600">{expiry?.recommended_action}</p>
              <p className="mt-3 text-sm text-slate-500">{expiry?.explanation}</p>
            </div>

            <div className="rounded-[1.6rem] border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Route optimization</p>
              <h3 className="mt-3 text-2xl font-semibold text-slate-950">{route ? `${route.total_eta_minutes} min ETA` : "Routing..."}</h3>
              <p className="mt-2 text-sm text-slate-600">{route?.summary ?? "Estimating the fastest delivery suggestion from donor pickup to the best-fit NGO destination."}</p>
              <div className="mt-4 space-y-3">
                {route?.stops.map((stop) => (
                  <div key={stop.request_id} className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-700 ring-1 ring-slate-200">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-semibold text-slate-950">{stop.priority_label}: {stop.ngo_name}</span>
                      <AIBadge label={stop.feasible ? "Feasible" : "Not Feasible"} tone={stop.feasible ? "violet" : "rose"} detail={`${stop.cumulative_eta_minutes} min`} />
                    </div>
                    <p className="mt-2">{stop.area} · {stop.distance_km.toFixed(1)} km · {stop.time_left_hours}h safe time left</p>
                    <p className="mt-2 text-slate-500">{stop.feasibility_reason}</p>
                  </div>
                ))}
              </div>
            </div>

            {match?.matches.length ? (
              <div className="rounded-[1.6rem] border border-slate-200 bg-white p-5 shadow-sm">
                <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Candidate feasibility</p>
                <div className="mt-4 space-y-3">
                  {match.matches.slice(0, 3).map((candidate) => (
                    <div key={candidate.request_id} className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-700 ring-1 ring-slate-200">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="font-semibold text-slate-950">{candidate.ngo_name}</span>
                        <AIBadge label={candidate.feasible ? "Feasible" : "Not Feasible"} tone={candidate.feasible ? "emerald" : "rose"} detail={`${candidate.fit_percentage.toFixed(0)}% fit`} />
                      </div>
                      <p className="mt-2">ETA {candidate.eta_minutes} min · Time left {candidate.time_left_hours}h · Final status {candidate.final_status}</p>
                      <p className="mt-2 text-slate-500">{candidate.feasibility_reason}</p>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      ) : (
        <div className="rounded-[1.6rem] border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-600">Select a donation to load AI recommendations.</div>
      )}
    </SectionCard>
  );
}
