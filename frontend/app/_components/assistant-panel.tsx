"use client";

import { useState, useTransition } from "react";

import { SectionCard } from "@/app/_components/section-card";
import { askAI } from "@/app/_lib/ai";
import type { AIAssistantResponse } from "@/app/_lib/types";

const defaultPrompts = [
  "Which donation should be prioritized today?",
  "Which NGO is best for this donation?",
  "What is the waste risk today?",
  "How many meals did we save?",
];

export function AssistantPanel({ title = "Ask AI", description = "Query the live board for prioritization, routing, and impact guidance." }: { title?: string; description?: string }) {
  const [question, setQuestion] = useState(defaultPrompts[0]);
  const [response, setResponse] = useState<AIAssistantResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function submit() {
    setError(null);
    startTransition(() => {
      void askAI({ question })
        .then((result) => {
          setResponse(result);
        })
        .catch((caughtError: unknown) => {
          setError(caughtError instanceof Error ? caughtError.message : "Unable to reach the AI assistant.");
        });
    });
  }

  return (
    <SectionCard title={title} description={description}>
      <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {defaultPrompts.map((prompt) => (
              <button
                key={prompt}
                type="button"
                onClick={() => setQuestion(prompt)}
                className="rounded-full border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-white"
              >
                {prompt}
              </button>
            ))}
          </div>
          <textarea
            rows={5}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            className="w-full rounded-[1.5rem] border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none"
          />
          <button
            type="button"
            onClick={submit}
            disabled={isPending || question.trim().length < 2}
            className="rounded-full bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {isPending ? "Thinking..." : "Ask AI"}
          </button>
          {error ? <p className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</p> : null}
        </div>

        <div className="rounded-[1.8rem] border border-slate-200 bg-slate-50/70 p-5">
          {response ? (
            <div className="space-y-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.28em] text-sky-700">AI response</p>
                <h3 className="mt-2 text-xl font-semibold text-slate-950">{response.answer}</h3>
              </div>
              <div className="space-y-2">
                {response.bullet_points.map((point) => (
                  <p key={point} className="rounded-2xl bg-white px-4 py-3 text-sm text-slate-700 ring-1 ring-slate-200">
                    {point}
                  </p>
                ))}
              </div>
              <div className="flex flex-wrap gap-2">
                {response.follow_up_prompts.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => setQuestion(prompt)}
                    className="rounded-full bg-white px-3 py-2 text-xs font-semibold text-slate-700 ring-1 ring-slate-200 transition hover:bg-slate-50"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex h-full min-h-52 items-center justify-center rounded-[1.5rem] border border-dashed border-slate-300 bg-white px-6 text-center text-sm text-slate-500">
              Ask about prioritization, best NGO match, waste risk, or live impact to see the copilot reasoning.
            </div>
          )}
        </div>
      </div>
    </SectionCard>
  );
}
