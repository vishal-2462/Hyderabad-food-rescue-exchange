import { API_BASE_URL } from "@/app/_lib/api-config";
import type {
  AIAssistantRequest,
  AIAssistantResponse,
  AIImpactForecastResponse,
  AIImpactSummaryResponse,
  AIMatchResponse,
  Donation,
  ExpiryPredictionResponse,
  FoodImageAnalysisResponse,
  RouteOptimizationRequest,
  RouteOptimizationResponse,
  WasteRiskResponse,
} from "@/app/_lib/types";

async function readError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? `Request failed with ${response.status}`;
  } catch {
    return `Request failed with ${response.status}`;
  }
}

async function fetchAiJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await readError(response));
  }

  return (await response.json()) as T;
}

function inferStorageCondition(donation: Donation): string {
  if (donation.storage_condition) {
    return donation.storage_condition;
  }
  const notes = donation.notes.toLowerCase();
  if (notes.includes("chill") || notes.includes("refriger")) {
    return "chilled";
  }
  if (notes.includes("insulated")) {
    return "insulated";
  }
  return "ambient";
}

export function getAIMatch(donationId: string): Promise<AIMatchResponse> {
  return fetchAiJson<AIMatchResponse>(`/ai/match/${donationId}`);
}

export function getWasteRisk(donationId: string): Promise<WasteRiskResponse> {
  return fetchAiJson<WasteRiskResponse>(`/ai/waste-risk/${donationId}`);
}

export function optimizeRoute(payload: RouteOptimizationRequest): Promise<RouteOptimizationResponse> {
  return fetchAiJson<RouteOptimizationResponse>("/ai/optimize-route", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function predictExpiryForDonation(donation: Donation): Promise<ExpiryPredictionResponse> {
  return fetchAiJson<ExpiryPredictionResponse>("/ai/analyze-freshness", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      food_type: donation.food_type,
      food_category: undefined,
      prepared_time: donation.prepared_time,
      storage_condition: inferStorageCondition(donation),
      quantity: donation.quantity,
      image_label: donation.image_freshness_label ?? undefined,
      visual_label: donation.image_visual_label ?? undefined,
      visual_confidence: donation.image_visual_confidence ?? undefined,
      shelf_life_hours: donation.shelf_life_hours ?? undefined,
    }),
  });
}

export function getAIImpactSummary(): Promise<AIImpactSummaryResponse> {
  return fetchAiJson<AIImpactSummaryResponse>("/ai/impact-summary");
}

export function getAIImpactForecast(): Promise<AIImpactForecastResponse> {
  return fetchAiJson<AIImpactForecastResponse>("/ai/impact-forecast");
}

export function askAI(payload: AIAssistantRequest): Promise<AIAssistantResponse> {
  return fetchAiJson<AIAssistantResponse>("/ai/assistant", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export async function analyzeFoodImage(file: File): Promise<FoodImageAnalysisResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/ai/analyze-food-image`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await readError(response));
  }

  return (await response.json()) as FoodImageAnalysisResponse;
}
