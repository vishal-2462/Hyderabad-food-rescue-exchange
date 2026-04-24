"use client";

import { useEffect, useMemo, useState } from "react";

import { AIBadge } from "@/app/_components/ai-badge";
import { SectionCard } from "@/app/_components/section-card";
import { getAIImpactSummary, getAIMatch, getWasteRisk, optimizeRoute } from "@/app/_lib/ai";
import type { AIImpactSummaryResponse, AIMatchResponse, Donation, RouteOptimizationResponse, WasteRiskResponse } from "@/app/_lib/types";

export function OverviewAIInsights({ donations }: { donations: Donation[] }) {
  const activeDonations = useMemo(
    () => donations.filter((donation) => ["available", "requested", "reserved", "picked_up"].includes(donation.status)).slice(0, 6),
    [donations],
  );
  const [summary, setSummary] = useState<AIImpactSummaryResponse | null>(null);
  const [topRisk, setTopRisk] = useState<WasteRiskResponse | null>(null);
  const [topMatch, setTopMatch] = useState<AIMatchResponse | null>(null);
  const [route, setRoute] = useState<RouteOptimizationResponse | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const summaryResult = await getAIImpactSummary();
        if (!cancelled) {
          setSummary(summaryResult);
        }
      } catch {
        if (!cancelled) {
          setSummary(null);
        }
      }

      if (activeDonations.length === 0) {
        return;
      }

      try {
        const risks = await Promise.all(activeDonations.map((donation) => getWasteRisk(donation.id)));
        if (cancelled) {
          return;
        }
        const highestRisk = risks.sort((left, right) => right.risk_score - left.risk_score)[0] ?? null;
        setTopRisk(highestRisk);
        if (!highestRisk) {
          return;
        }

        const [matchResult, routeResult] = await Promise.all([
          getAIMatch(highestRisk.donation_id),
          optimizeRoute({ donation_id: highestRisk.donation_id }),
        ]);
        if (!cancelled) {
          setTopMatch(matchResult);
          setRoute(routeResult);
        }
      } catch {
        if (!cancelled) {
          setTopRisk(null);
          setTopMatch(null);
          setRoute(null);
        }
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, [activeDonations]);

  const topDonation = topRisk ? activeDonations.find((donation) => donation.id === topRisk.donation_id) : null;

  return (
    <SectionCard title="AI Intelligence" description="Live rescue signals generated from matching, expiry, logistics, and waste-risk models.">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-[1.7rem] bg-slate-950 p-5 text-white">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-sky-300">Top priority</p>
          <h3 className="mt-3 text-2xl font-semibold">{topDonation?.title ?? "Loading AI signal"}</h3>
          <p className="mt-2 text-sm text-slate-300">{topRisk ? `Predicted waste risk: ${topRisk.risk_label} (${topRisk.risk_score.toFixed(0)}/100)` : "Calculating which live donation needs the fastest intervention."}</p>
          {topRisk ? <div className="mt-4"><AIBadge label="Prioritize now" tone={topRisk.risk_label === "high" ? "rose" : topRisk.risk_label === "medium" ? "amber" : "emerald"} detail={`${topRisk.safe_hours_remaining}h safe`} /></div> : null}
        </div>

        <div className="rounded-[1.7rem] border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Best NGO fit</p>
          <h3 className="mt-3 text-2xl font-semibold text-slate-950">{topMatch?.best_match?.ngo_name ?? "Waiting for match"}</h3>
          <p className="mt-2 text-sm text-slate-600">{topMatch?.best_match ? `${topMatch.best_match.fit_percentage.toFixed(1)}% fit with ${topMatch.best_match.confidence_percentage.toFixed(1)}% confidence.` : "The smart matching engine is ranking the strongest partner for the highest-risk donation."}</p>
          {topMatch?.best_match ? <div className="mt-4 flex flex-wrap gap-2">{topMatch.best_match.reasons.slice(0, 2).map((reason) => <AIBadge key={reason} label={reason} tone="sky" />)}</div> : null}
        </div>

        <div className="rounded-[1.7rem] border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Fastest route</p>
          <h3 className="mt-3 text-2xl font-semibold text-slate-950">{route ? `${route.total_eta_minutes} min` : "Planning"}</h3>
          <p className="mt-2 text-sm text-slate-600">{route?.summary ?? "Estimating the best Hyderabad dispatch route from donor pickup to the strongest NGO fit."}</p>
          {route?.stops[0] ? <div className="mt-4"><AIBadge label="Route optimized" tone="violet" detail={route.stops[0].ngo_name} /></div> : null}
        </div>

        <div className="rounded-[1.7rem] border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Next-week projection</p>
          <h3 className="mt-3 text-2xl font-semibold text-slate-950">{summary ? summary.expected_meals_next_week.toString() : "..."}</h3>
          <p className="mt-2 text-sm text-slate-600">{summary ? `Estimated meals saved next week with ${summary.weekly_growth_pct.toFixed(1)}% growth over the current snapshot.` : "Projecting the coming week from live throughput and open demand."}</p>
          {summary?.high_need_zones[0] ? <div className="mt-4"><AIBadge label="High-need zone" tone="amber" detail={summary.high_need_zones[0].area} /></div> : null}
        </div>
      </div>
    </SectionCard>
  );
}
