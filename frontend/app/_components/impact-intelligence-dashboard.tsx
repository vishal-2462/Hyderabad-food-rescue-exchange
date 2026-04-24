"use client";

import { useEffect, useState } from "react";

import { AIBadge } from "@/app/_components/ai-badge";
import { SectionCard } from "@/app/_components/section-card";
import { getAIImpactForecast, getAIImpactSummary } from "@/app/_lib/ai";
import type { AIImpactForecastResponse, AIImpactSummaryResponse } from "@/app/_lib/types";

export function ImpactIntelligenceDashboard() {
  const [summary, setSummary] = useState<AIImpactSummaryResponse | null>(null);
  const [forecast, setForecast] = useState<AIImpactForecastResponse | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [summaryResult, forecastResult] = await Promise.all([getAIImpactSummary(), getAIImpactForecast()]);
        if (!cancelled) {
          setSummary(summaryResult);
          setForecast(forecastResult);
        }
      } catch {
        if (!cancelled) {
          setSummary(null);
          setForecast(null);
        }
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <SectionCard title="AI Impact Intelligence" description="Predictive signals for meals saved, waste reduction, corridor pressure, and next-week delivery outlook.">
      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-[1.6rem] bg-slate-950 p-5 text-white">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-sky-300">Meals saved this week</p>
            <p className="mt-3 text-4xl font-semibold">{summary?.meals_saved_this_week ?? "--"}</p>
            <p className="mt-2 text-sm text-slate-300">Current measured rescue volume from delivered food recovery.</p>
          </div>
          <div className="rounded-[1.6rem] bg-white p-5 ring-1 ring-slate-200">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Forecast next week</p>
            <p className="mt-3 text-4xl font-semibold text-slate-950">{forecast?.projected_meals_saved_next_week ?? "--"}</p>
            <p className="mt-2 text-sm text-slate-600">Projected meals based on current throughput and open request pressure.</p>
          </div>
          <div className="rounded-[1.6rem] bg-white p-5 ring-1 ring-slate-200">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Waste prevented</p>
            <p className="mt-3 text-4xl font-semibold text-slate-950">{summary ? `${summary.waste_reduced_kg} kg` : "--"}</p>
            <p className="mt-2 text-sm text-slate-600">Recovered kilograms converted into impact-ready waste prevention output.</p>
          </div>
          <div className="rounded-[1.6rem] bg-white p-5 ring-1 ring-slate-200">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Top demand zone</p>
            <p className="mt-3 text-3xl font-semibold text-slate-950">{summary?.high_need_zones[0]?.area ?? "--"}</p>
            <p className="mt-2 text-sm text-slate-600">The corridor with the highest active request pressure right now.</p>
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-[1.6rem] border border-slate-200 bg-white p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">7-day forecast</p>
                <h3 className="mt-2 text-2xl font-semibold text-slate-950">Projected rescue trend</h3>
              </div>
              {forecast ? <AIBadge label={forecast.trend_direction === "up" ? "Trend up" : "Trend stable"} tone="sky" detail={`${forecast.confidence_percentage.toFixed(0)}% confidence`} /> : null}
            </div>
            <div className="mt-5 grid gap-3">
              {forecast?.forecast.map((point) => (
                <div key={point.label} className="space-y-2">
                  <div className="flex items-center justify-between text-sm font-medium text-slate-700">
                    <span>{point.label}</span>
                    <span>{point.predicted_meals_saved} meals</span>
                  </div>
                  <div className="h-3 rounded-full bg-slate-100">
                    <div className="h-3 rounded-full bg-gradient-to-r from-sky-500 via-indigo-500 to-violet-500" style={{ width: `${Math.min((point.predicted_meals_saved / Math.max(forecast.projected_meals_saved_next_week, 1)) * 100 * 4, 100)}%` }} />
                  </div>
                </div>
              )) ?? <p className="text-sm text-slate-500">Loading forecast...</p>}
            </div>
          </div>

          <div className="rounded-[1.6rem] border border-slate-200 bg-white p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Why the forecast looks this way</p>
            <div className="mt-4 space-y-3">
              {(summary?.explanation ?? [forecast?.explanation ?? "Waiting for the forecast narrative..."]).map((item) => (
                <p key={item} className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-700">
                  {item}
                </p>
              ))}
            </div>
          </div>
        </div>
      </div>
    </SectionCard>
  );
}
