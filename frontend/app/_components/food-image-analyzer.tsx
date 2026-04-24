"use client";

import { useState, useTransition } from "react";

import { AIBadge } from "@/app/_components/ai-badge";
import { analyzeFoodImage } from "@/app/_lib/ai";
import type { FoodImageAnalysisResponse } from "@/app/_lib/types";

export function FoodImageAnalyzer({ onApply }: { onApply?: (analysis: FoodImageAnalysisResponse) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<FoodImageAnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  return (
    <div className="rounded-[1.6rem] border border-slate-200 bg-slate-50/70 p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Food image recognition</p>
          <h3 className="mt-2 text-lg font-semibold text-slate-950">Analyze a food image before posting</h3>
          <p className="mt-1 text-sm text-slate-600">Upload a food image to infer food category and a supporting visual freshness signal. Time of preparation remains the primary decision input.</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <input type="file" accept="image/*" onChange={(event) => setFile(event.target.files?.[0] ?? null)} className="text-sm text-slate-600" />
          <button
            type="button"
            onClick={() => {
              if (!file) {
                return;
              }
              setError(null);
              startTransition(() => {
                void analyzeFoodImage(file)
                  .then((analysis) => {
                    setResult(analysis);
                    onApply?.(analysis);
                  })
                  .catch((caughtError: unknown) => {
                    setError(caughtError instanceof Error ? caughtError.message : "Unable to analyze the image.");
                  });
              });
            }}
            disabled={!file || isPending}
            className="rounded-full bg-slate-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {isPending ? "Analyzing..." : "Analyze image"}
          </button>
        </div>
      </div>

      {error ? <p className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</p> : null}

      {result ? (
        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-2xl bg-white p-4 ring-1 ring-slate-200">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Predicted category</p>
            <p className="mt-2 text-lg font-semibold text-slate-950">{result.food_type_guess}</p>
            <p className="mt-2 text-sm text-slate-600 capitalize">{result.food_category.replaceAll("_", " ")}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <AIBadge label={`Confidence ${result.confidence_bucket}`} tone={result.confidence_bucket === "high" ? "emerald" : result.confidence_bucket === "medium" ? "amber" : "slate"} detail={`${(result.category_confidence * 100).toFixed(0)}%`} />
              {result.category_uncertain ? <AIBadge label="Category uncertain" tone="rose" /> : <AIBadge label="Category stable" tone="sky" />}
            </div>
          </div>
          <div className="rounded-2xl bg-white p-4 ring-1 ring-slate-200">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Visual state</p>
            <p className="mt-2 text-lg font-semibold capitalize text-slate-950">{result.visual_label.replaceAll("_", " ")}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <AIBadge label={result.image_label === "spoiled" ? "Visual Spoilage Detected" : result.image_label === "medium" ? "Borderline Visual Signal" : "Visually Acceptable"} tone={result.image_label === "spoiled" ? "rose" : result.image_label === "medium" ? "amber" : "emerald"} />
              <AIBadge label="Visual confidence" tone="slate" detail={`${result.visual_confidence.toFixed(0)}%`} />
            </div>
          </div>
          <div className="rounded-2xl bg-white p-4 ring-1 ring-slate-200">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Packaging quality</p>
            <p className="mt-2 text-lg font-semibold capitalize text-slate-950">{result.packaging_quality}</p>
            <p className="mt-2 text-sm text-slate-600">{result.quantity_estimate}</p>
          </div>
          <div className="rounded-2xl bg-white p-4 ring-1 ring-slate-200">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Supporting inference</p>
            <p className="mt-2 text-sm font-medium text-slate-900">{result.distribution_urgency}</p>
            <p className="mt-2 text-sm text-slate-600">{result.suggested_storage}</p>
            <p className="mt-2 text-xs text-slate-500">Model route: {result.model_key} · Version: {result.model_version}</p>
          </div>
          <div className="rounded-2xl bg-white p-4 text-sm text-slate-600 ring-1 ring-slate-200 md:col-span-2">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Possible matches</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {result.top_categories.map((candidate) => (
                <AIBadge key={candidate.label} label={candidate.label.replaceAll("_", " ")} tone="slate" detail={`${(candidate.confidence * 100).toFixed(0)}%`} />
              ))}
            </div>
            {result.category_uncertain && result.uncertainty_reason ? <p className="mt-3 text-sm text-rose-700">{result.uncertainty_reason}</p> : null}
          </div>
          <div className="rounded-2xl bg-white p-4 text-sm text-slate-600 ring-1 ring-slate-200 md:col-span-2 xl:col-span-4">
            {result.explanation}
          </div>
        </div>
      ) : null}
    </div>
  );
}
