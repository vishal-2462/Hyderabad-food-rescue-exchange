from __future__ import annotations

from dataclasses import dataclass
import os
from datetime import datetime, timezone

from app.models import Donation, Donor, NGO, Request, RequestStatus
from app.services.freshness_engine import analyze_donation_freshness, delivery_feasibility
from app.services.matching import haversine_km


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(value, upper))


MATCHING_WEIGHTS = {
    "distance": 0.2,
    "capacity": 0.15,
    "quantity_fit": 0.14,
    "urgency_fit": 0.16,
    "category_fit": 0.12,
    "acceptance_likelihood": 0.11,
    "demand_pressure": 0.12,
}

ROUTE_SPEED_KMPH = float(os.getenv("AI_ROUTE_SPEED_KMPH", "26"))


FOCUS_ALIASES = {
    "prepared_food": {"prepared_food", "community_meals"},
    "dry_rations": {"dry_rations", "night_shelter"},
    "bakery": {"bakery", "community_meals"},
}


@dataclass(slots=True)
class AIScoreBreakdown:
    distance: float
    capacity: float
    quantity_fit: float
    urgency_fit: float
    category_fit: float
    acceptance_likelihood: float
    demand_pressure: float


@dataclass(slots=True)
class AIRecommendedMatch:
    request_id: str
    ngo_id: str
    ngo_name: str
    request_title: str
    food_category: str
    fit_percentage: float
    confidence_percentage: float
    distance_km: float
    eta_minutes: int
    time_left_hours: float
    feasible: bool
    feasibility_reason: str
    visual_label: str | None
    visual_confidence: float | None
    time_based_status: str
    final_status: str
    reasons: list[str]
    explanation: str
    breakdown: AIScoreBreakdown


def _focus_fit(donation: Donation, ngo: NGO) -> float:
    focus_terms = set(ngo.focus_areas)
    aliases = FOCUS_ALIASES.get(donation.category, {donation.category})
    return 1.0 if focus_terms.intersection(aliases) else 0.45


def _quantity_fit(donation: Donation, request: Request) -> float:
    spread = abs(donation.quantity - request.quantity_needed)
    baseline = max(donation.quantity, request.quantity_needed, 1)
    return _clamp(1 - (spread / baseline))


def _estimate_eta_minutes(distance_km: float) -> int:
    return max(int(round((distance_km / max(ROUTE_SPEED_KMPH, 1)) * 60)) + 4, 6)


def _urgency_fit(time_left_hours: float, request: Request, reference_time: datetime) -> float:
    hours_to_expiry = max(time_left_hours, 0.05)
    hours_to_need = max((request.needed_by - reference_time).total_seconds() / 3600, 0.1)
    alignment = _clamp(1 - (abs(hours_to_expiry - hours_to_need) / 12))
    expiry_pressure = 1.0 if hours_to_expiry <= 3 else 0.85 if hours_to_expiry <= 6 else 0.65 if hours_to_expiry <= 10 else 0.45
    return _clamp((0.55 * alignment) + (0.45 * max(request.priority / 5, expiry_pressure)))


def _acceptance_likelihood(ngo: NGO) -> float:
    spare_capacity = ngo.remaining_capacity / max(ngo.max_daily_capacity, 1)
    return _clamp((0.62 * (ngo.reliability / 100)) + (0.38 * spare_capacity))


def _demand_pressure(donation: Donation, request: Request) -> float:
    meal_pressure = min(request.people_served / max(donation.meals_estimate or donation.quantity, 1), 1.0)
    quantity_pressure = min(request.quantity_needed / max(donation.quantity, 1), 1.0)
    return _clamp((0.45 * quantity_pressure) + (0.3 * meal_pressure) + (0.25 * (request.priority / 5)))


def _top_reasons(distance: float, capacity: float, quantity_fit: float, urgency_fit: float, category_fit: float, acceptance_likelihood: float, demand_pressure: float, feasible: bool, feasibility_reason: str) -> list[str]:
    ranked = [
        (distance, "Near pickup corridor"),
        (capacity, "Can absorb the full quantity"),
        (quantity_fit, "Quantity closely matches demand"),
        (urgency_fit, "Strong fit for the current expiry window"),
        (category_fit, "NGO focus aligns with this food type"),
        (acceptance_likelihood, "Reliable response profile"),
        (demand_pressure, "High demand pressure for this donation"),
    ]
    labels = [label for _, label in sorted(ranked, key=lambda item: item[0], reverse=True)[:3]]
    labels.append("Feasible within safe window" if feasible else feasibility_reason)
    return labels[:3]


def rank_ai_matches(
    donation: Donation,
    requests: list[Request],
    ngos_by_id: dict[str, NGO],
    donors_by_id: dict[str, Donor],
    *,
    now: datetime | None = None,
) -> list[AIRecommendedMatch]:
    reference_time = now or datetime.now(timezone.utc)
    donor = donors_by_id[donation.donor_id]
    freshness = analyze_donation_freshness(donation, current_time=reference_time)

    best_by_ngo: dict[str, AIRecommendedMatch] = {}
    for request in requests:
        if request.status not in {RequestStatus.OPEN, RequestStatus.REQUESTED, RequestStatus.MATCHED}:
            continue
        if request.category != donation.category:
            continue
        if request.matched_donation_id is not None and request.matched_donation_id != donation.id:
            continue

        ngo = ngos_by_id[request.ngo_id]
        distance_km = haversine_km(
            donation.location.lat,
            donation.location.lng,
            request.location.lat,
            request.location.lng,
        )
        distance_limit = max(request.max_distance_km, donor.preferred_radius_km, 1.0)
        distance_score = _clamp(1 - (distance_km / distance_limit))
        eta_minutes = _estimate_eta_minutes(distance_km)
        feasible, feasibility_reason = delivery_feasibility(
            eta_minutes=eta_minutes,
            time_left_hours=freshness.time_left_hours,
            final_status=freshness.final_status,
        )
        capacity_score = _clamp(ngo.remaining_capacity / max(donation.quantity, 1))
        quantity_fit = _quantity_fit(donation, request)
        urgency_fit = _urgency_fit(freshness.time_left_hours, request, reference_time)
        category_fit = _focus_fit(donation, ngo)
        acceptance_likelihood = _acceptance_likelihood(ngo)
        demand_pressure = _demand_pressure(donation, request)

        total_score = (
            (MATCHING_WEIGHTS["distance"] * distance_score)
            + (MATCHING_WEIGHTS["capacity"] * capacity_score)
            + (MATCHING_WEIGHTS["quantity_fit"] * quantity_fit)
            + (MATCHING_WEIGHTS["urgency_fit"] * urgency_fit)
            + (MATCHING_WEIGHTS["category_fit"] * category_fit)
            + (MATCHING_WEIGHTS["acceptance_likelihood"] * acceptance_likelihood)
            + (MATCHING_WEIGHTS["demand_pressure"] * demand_pressure)
        )

        if capacity_score == 0:
            total_score *= 0.45
        if not feasible:
            total_score *= 0.18

        fit_percentage = round(total_score * 100, 1)
        confidence_percentage = round(((0.58 * total_score) + (0.42 * ((category_fit + acceptance_likelihood + urgency_fit) / 3))) * 100, 1)
        reasons = _top_reasons(distance_score, capacity_score, quantity_fit, urgency_fit, category_fit, acceptance_likelihood, demand_pressure, feasible, feasibility_reason)
        explanation = (
            f"{ngo.name} is {distance_km:.1f} km away, has {ngo.remaining_capacity} units of spare capacity, "
            f"and would take about {eta_minutes} minutes to reach while the donation has {freshness.time_left_hours:.2f}h left. {feasibility_reason}"
        )

        result = AIRecommendedMatch(
            request_id=request.id,
            ngo_id=ngo.id,
            ngo_name=ngo.name,
            request_title=request.title,
            fit_percentage=fit_percentage,
            confidence_percentage=confidence_percentage,
            distance_km=round(distance_km, 1),
            eta_minutes=eta_minutes,
            time_left_hours=freshness.time_left_hours,
            feasible=feasible,
            feasibility_reason=feasibility_reason,
            food_category=freshness.food_category,
            visual_label=freshness.visual_label,
            visual_confidence=freshness.visual_confidence,
            time_based_status=freshness.time_based_status,
            final_status=freshness.final_status,
            reasons=reasons,
            explanation=explanation,
            breakdown=AIScoreBreakdown(
                distance=round(distance_score * 100, 1),
                capacity=round(capacity_score * 100, 1),
                quantity_fit=round(quantity_fit * 100, 1),
                urgency_fit=round(urgency_fit * 100, 1),
                category_fit=round(category_fit * 100, 1),
                acceptance_likelihood=round(acceptance_likelihood * 100, 1),
                demand_pressure=round(demand_pressure * 100, 1),
            ),
        )

        current = best_by_ngo.get(ngo.id)
        if current is None or result.fit_percentage > current.fit_percentage:
            best_by_ngo[ngo.id] = result

    return sorted(best_by_ngo.values(), key=lambda item: (not item.feasible, -item.fit_percentage, item.distance_km, item.ngo_name.lower()))
