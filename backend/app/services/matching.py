from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import asin, cos, radians, sin, sqrt

from app.models import Donation, Donor, NGO, Request, RequestStatus


@dataclass(slots=True)
class MatchBreakdown:
    distance: float
    expiry_urgency: float
    safety_window: float
    capacity: float
    demand: float
    reliability: float


@dataclass(slots=True)
class MatchResult:
    request_id: str
    ngo_id: str
    request_title: str
    ngo_name: str
    total_score: float
    distance_km: float
    factor_scores: MatchBreakdown
    explanation: str


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius_km = 6371.0
    lat_delta = radians(lat2 - lat1)
    lng_delta = radians(lng2 - lng1)
    lat1_r = radians(lat1)
    lat2_r = radians(lat2)

    a = sin(lat_delta / 2) ** 2 + cos(lat1_r) * cos(lat2_r) * sin(lng_delta / 2) ** 2
    c = 2 * asin(sqrt(a))
    return radius_km * c


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(value, upper))


def _round_percent(score: float) -> float:
    return round(score * 100, 1)


def rank_matches(
    donation: Donation,
    requests: list[Request],
    ngos_by_id: dict[str, NGO],
    donors_by_id: dict[str, Donor],
    now: datetime | None = None,
) -> list[MatchResult]:
    reference_time = now or datetime.now(timezone.utc)
    donor = donors_by_id[donation.donor_id]
    hours_to_expiry = max((donation.expires_at - reference_time).total_seconds() / 3600, 0.1)
    safe_until = donation.expires_at - timedelta(hours=donation.safety_window_hours)

    results: list[MatchResult] = []
    for request in requests:
        if request.status not in {RequestStatus.OPEN, RequestStatus.REQUESTED, RequestStatus.MATCHED}:
            continue
        if request.matched_donation_id is not None and request.matched_donation_id != donation.id:
            continue
        if request.category != donation.category:
            continue

        ngo = ngos_by_id[request.ngo_id]
        distance_km = haversine_km(
            donation.location.lat,
            donation.location.lng,
            request.location.lat,
            request.location.lng,
        )
        travel_time_hours = max(distance_km / 24.0, 0.25)
        hours_to_need = max((request.needed_by - reference_time).total_seconds() / 3600, 0.0)
        time_alignment = 1 - min(abs(hours_to_need - hours_to_expiry), 24) / 24

        distance_score = _clamp(1 - (distance_km / max(request.max_distance_km, 1.0)))
        urgency_base = 1.0 if hours_to_expiry <= 6 else 0.8 if hours_to_expiry <= 12 else 0.65
        expiry_urgency_score = _clamp((0.55 * time_alignment) + (0.45 * max(request.priority / 5, urgency_base)))

        usable_window_hours = (safe_until - reference_time).total_seconds() / 3600
        safety_margin_hours = usable_window_hours - travel_time_hours
        if safety_margin_hours <= 0.5:
            safety_window_score = 0.0
        else:
            safety_window_score = _clamp(safety_margin_hours / max(donation.safety_window_hours + 4, 4))

        capacity_score = _clamp(ngo.remaining_capacity / max(donation.quantity, 1))

        quantity_pressure = min(request.quantity_needed / max(donation.quantity, 1), 1.0)
        people_pressure = min(request.people_served / max(donation.meals_estimate or donation.quantity, 1), 1.0)
        demand_score = _clamp((0.5 * quantity_pressure) + (0.25 * people_pressure) + (0.25 * (request.priority / 5)))

        reliability_score = _clamp(((ngo.reliability + donor.reliability) / 2) / 100)

        total_score = (
            (0.27 * distance_score)
            + (0.18 * expiry_urgency_score)
            + (0.17 * safety_window_score)
            + (0.15 * capacity_score)
            + (0.13 * demand_score)
            + (0.10 * reliability_score)
        )

        if safety_window_score == 0 or capacity_score == 0:
            total_score *= 0.35

        explanation = (
            f"{ngo.name} is {distance_km:.1f} km away, has {ngo.remaining_capacity} units of spare capacity, "
            f"and can receive the donation with a {max(safety_margin_hours, 0):.1f}h safety buffer."
        )

        results.append(
            MatchResult(
                request_id=request.id,
                ngo_id=ngo.id,
                request_title=request.title,
                ngo_name=ngo.name,
                total_score=round(total_score * 100, 1),
                distance_km=round(distance_km, 1),
                factor_scores=MatchBreakdown(
                    distance=_round_percent(distance_score),
                    expiry_urgency=_round_percent(expiry_urgency_score),
                    safety_window=_round_percent(safety_window_score),
                    capacity=_round_percent(capacity_score),
                    demand=_round_percent(demand_score),
                    reliability=_round_percent(reliability_score),
                ),
                explanation=explanation,
            )
        )

    return sorted(
        results,
        key=lambda result: (-result.total_score, result.distance_km, result.request_title.lower()),
    )
