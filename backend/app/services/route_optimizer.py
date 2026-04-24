from __future__ import annotations

import os
from dataclasses import dataclass

from app.models import Donation, NGO, Request
from app.services.ai_matching import rank_ai_matches
from app.services.matching import haversine_km

DEFAULT_ROUTE_SPEED_KMPH = float(os.getenv("AI_ROUTE_SPEED_KMPH", "26"))


@dataclass(slots=True)
class RouteStopRecommendation:
    request_id: str
    ngo_id: str
    ngo_name: str
    area: str
    distance_km: float
    eta_minutes_from_previous: int
    cumulative_eta_minutes: int
    priority_label: str
    time_left_hours: float
    feasible: bool
    feasibility_reason: str


@dataclass(slots=True)
class RouteOptimizationResult:
    total_distance_km: float
    total_eta_minutes: int
    summary: str
    stops: list[RouteStopRecommendation]


def optimize_route(
    donation: Donation,
    candidate_requests: list[Request],
    ngos_by_id: dict[str, NGO],
    donors_by_id: dict[str, object],
) -> RouteOptimizationResult:
    if not candidate_requests:
        return RouteOptimizationResult(total_distance_km=0.0, total_eta_minutes=0, summary="No route recommendation is available yet.", stops=[])

    matches = rank_ai_matches(donation, candidate_requests, ngos_by_id, donors_by_id)
    if not matches:
        return RouteOptimizationResult(total_distance_km=0.0, total_eta_minutes=0, summary="No route recommendation is available yet.", stops=[])

    stops: list[RouteStopRecommendation] = []
    current_lat = donation.location.lat
    current_lng = donation.location.lng
    cumulative_eta = 0
    total_distance = 0.0

    for index, match in enumerate(matches[:3], start=1):
        request = next(request for request in candidate_requests if request.id == match.request_id)
        ngo = ngos_by_id[match.ngo_id]
        distance_km = haversine_km(current_lat, current_lng, request.location.lat, request.location.lng)
        eta_minutes = max(int(round((distance_km / max(DEFAULT_ROUTE_SPEED_KMPH, 1)) * 60)) + 4, 6)
        cumulative_eta += eta_minutes
        total_distance += distance_km
        stops.append(
            RouteStopRecommendation(
                request_id=request.id,
                ngo_id=ngo.id,
                ngo_name=ngo.name,
                area=request.location.area,
                distance_km=round(distance_km, 1),
                eta_minutes_from_previous=eta_minutes,
                cumulative_eta_minutes=cumulative_eta,
                priority_label=f"Stop {index}",
                time_left_hours=match.time_left_hours,
                feasible=match.feasible and (cumulative_eta / 60) <= match.time_left_hours,
                feasibility_reason=match.feasibility_reason if (cumulative_eta / 60) <= match.time_left_hours else "Not feasible: cumulative route ETA exceeds the remaining safe window.",
            )
        )
        current_lat = request.location.lat
        current_lng = request.location.lng

    summary = f"Fastest demo route starts with {stops[0].ngo_name} and reaches the first delivery in about {stops[0].cumulative_eta_minutes} min."
    return RouteOptimizationResult(
        total_distance_km=round(total_distance, 1),
        total_eta_minutes=cumulative_eta,
        summary=summary,
        stops=stops,
    )
