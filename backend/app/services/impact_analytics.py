from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

from app.models import Donation, DonationStatus, Donor, NGO, Request, RequestStatus


@dataclass(slots=True)
class AreaInsight:
    area: str
    request_count: int
    urgency_score: float
    explanation: str


@dataclass(slots=True)
class ActorInsight:
    actor_id: str
    actor_name: str
    metric_value: float
    explanation: str


@dataclass(slots=True)
class ImpactSummaryResult:
    snapshot_at: datetime
    meals_saved_this_week: int
    waste_reduced_kg: float
    co2_saved_kg: float
    expected_meals_next_week: int
    weekly_growth_pct: float
    high_need_zones: list[AreaInsight]
    top_donor: ActorInsight | None
    top_ngo: ActorInsight | None
    explanation: list[str]


@dataclass(slots=True)
class ForecastPoint:
    label: str
    predicted_meals_saved: int
    predicted_waste_reduced_kg: float
    predicted_open_requests: int


@dataclass(slots=True)
class ImpactForecastResult:
    snapshot_at: datetime
    trend_direction: str
    confidence_percentage: float
    projected_meals_saved_next_week: int
    projected_waste_reduced_kg_next_week: float
    high_need_zones: list[AreaInsight]
    forecast: list[ForecastPoint]
    explanation: str


def _high_need_zones(requests: list[Request]) -> list[AreaInsight]:
    by_area: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    for request in requests:
        if request.status not in {RequestStatus.OPEN, RequestStatus.REQUESTED, RequestStatus.MATCHED, RequestStatus.RESERVED}:
            continue
        counts[request.location.area] += 1
        by_area[request.location.area] += request.priority + min(request.people_served / 40, 3)

    ranked = sorted(by_area.items(), key=lambda item: (-item[1], item[0]))[:3]
    return [
        AreaInsight(
            area=area,
            request_count=counts[area],
            urgency_score=round(score, 1),
            explanation=f"{counts[area]} active requests are concentrated in {area}, making it a high-need corridor.",
        )
        for area, score in ranked
    ]


def summarize_impact_intelligence(
    donations: list[Donation],
    requests: list[Request],
    donors: list[Donor],
    ngos: list[NGO],
    *,
    now: datetime | None = None,
) -> ImpactSummaryResult:
    snapshot_at = now or datetime.now(timezone.utc)
    delivered = [donation for donation in donations if donation.status == DonationStatus.DELIVERED]
    meals_saved_this_week = sum(donation.meals_estimate for donation in delivered)
    waste_reduced_kg = round(sum(donation.quantity for donation in delivered), 1)
    co2_saved_kg = round(waste_reduced_kg * 2.5, 1)

    active_requests = [request for request in requests if request.status in {RequestStatus.OPEN, RequestStatus.REQUESTED, RequestStatus.MATCHED, RequestStatus.RESERVED}]
    expected_meals_next_week = int(round(meals_saved_this_week * 1.08 + (sum(request.people_served for request in active_requests[:4]) * 0.18)))
    weekly_growth_pct = round(((expected_meals_next_week - meals_saved_this_week) / max(meals_saved_this_week, 1)) * 100, 1)

    donor_scores = {donor.id: 0.0 for donor in donors}
    for donation in delivered:
        donor_scores[donation.donor_id] = donor_scores.get(donation.donor_id, 0.0) + donation.meals_estimate
    top_donor = None
    if donor_scores:
        donor_id = max(donor_scores, key=donor_scores.get)
        donor = next((item for item in donors if item.id == donor_id), None)
        if donor is not None:
            top_donor = ActorInsight(
                actor_id=donor.id,
                actor_name=donor.name,
                metric_value=donor_scores[donor.id],
                explanation=f"{donor.name} leads the network with {int(donor_scores[donor.id])} delivered meals in the current seed.",
            )

    ngo_scores = {ngo.id: 0.0 for ngo in ngos}
    for request in requests:
        if request.status in {RequestStatus.RESERVED, RequestStatus.FULFILLED}:
            ngo_scores[request.ngo_id] = ngo_scores.get(request.ngo_id, 0.0) + request.people_served
    top_ngo = None
    if ngo_scores:
        ngo_id = max(ngo_scores, key=ngo_scores.get)
        ngo = next((item for item in ngos if item.id == ngo_id), None)
        if ngo is not None:
            top_ngo = ActorInsight(
                actor_id=ngo.id,
                actor_name=ngo.name,
                metric_value=ngo_scores[ngo.id],
                explanation=f"{ngo.name} is positioned to serve {int(ngo_scores[ngo.id])} people across reserved and fulfilled requests.",
            )

    zones = _high_need_zones(requests)
    explanation = [
        f"Projected meals next week rise to {expected_meals_next_week} because open demand remains high in the top corridors.",
        f"Waste avoided currently sits at {waste_reduced_kg} kg, creating an estimated {co2_saved_kg} kg CO2e benefit.",
    ]
    return ImpactSummaryResult(
        snapshot_at=snapshot_at,
        meals_saved_this_week=meals_saved_this_week,
        waste_reduced_kg=waste_reduced_kg,
        co2_saved_kg=co2_saved_kg,
        expected_meals_next_week=expected_meals_next_week,
        weekly_growth_pct=weekly_growth_pct,
        high_need_zones=zones,
        top_donor=top_donor,
        top_ngo=top_ngo,
        explanation=explanation,
    )


def forecast_impact(
    donations: list[Donation],
    requests: list[Request],
    donors: list[Donor],
    ngos: list[NGO],
    *,
    now: datetime | None = None,
) -> ImpactForecastResult:
    snapshot_at = now or datetime.now(timezone.utc)
    summary = summarize_impact_intelligence(donations, requests, donors, ngos, now=snapshot_at)
    active_requests = [request for request in requests if request.status in {RequestStatus.OPEN, RequestStatus.REQUESTED, RequestStatus.MATCHED, RequestStatus.RESERVED}]

    daily_base = max(summary.expected_meals_next_week / 7, 12)
    request_pressure = max(len(active_requests), 1)
    multipliers = [0.94, 1.02, 1.08, 1.12, 1.04, 0.95, 0.91]
    labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    forecast = [
        ForecastPoint(
            label=label,
            predicted_meals_saved=int(round(daily_base * multiplier)),
            predicted_waste_reduced_kg=round(daily_base * multiplier * 0.36, 1),
            predicted_open_requests=max(int(round(request_pressure * (1.02 if multiplier > 1 else 0.96))), 1),
        )
        for label, multiplier in zip(labels, multipliers, strict=True)
    ]
    projected_meals = sum(point.predicted_meals_saved for point in forecast)
    projected_waste = round(sum(point.predicted_waste_reduced_kg for point in forecast), 1)
    trend_direction = "up" if summary.weekly_growth_pct >= 0 else "down"

    return ImpactForecastResult(
        snapshot_at=snapshot_at,
        trend_direction=trend_direction,
        confidence_percentage=86.0,
        projected_meals_saved_next_week=projected_meals,
        projected_waste_reduced_kg_next_week=projected_waste,
        high_need_zones=summary.high_need_zones,
        forecast=forecast,
        explanation="The forecast blends current delivery throughput with open request pressure to produce a stable demo projection.",
    )
