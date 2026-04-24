from __future__ import annotations

from dataclasses import dataclass

from app.models import Donation, DonationStatus, Donor, NGO, Request, RequestStatus
from app.services.ai_matching import rank_ai_matches
from app.services.freshness_engine import analyze_donation_freshness


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(value, upper))


@dataclass(slots=True)
class WasteRiskResult:
    donation_id: str
    risk_score: float
    risk_label: str
    final_status: str
    top_reasons: list[str]
    recommended_action: str
    safe_hours_remaining: float
    best_match_fit: float


def score_waste_risk(
    donation: Donation,
    requests: list[Request],
    ngos_by_id: dict[str, NGO],
    donors_by_id: dict[str, Donor],
) -> WasteRiskResult:
    freshness = analyze_donation_freshness(donation)
    relevant_requests = [request for request in requests if request.category == donation.category]
    ranked_matches = rank_ai_matches(donation, relevant_requests, ngos_by_id, donors_by_id)
    feasible_matches = [match for match in ranked_matches if match.feasible]
    best_match_fit = feasible_matches[0].fit_percentage if feasible_matches else ranked_matches[0].fit_percentage if ranked_matches else 0.0
    matched_request_count = sum(1 for request in relevant_requests if request.status in {RequestStatus.REQUESTED, RequestStatus.MATCHED, RequestStatus.RESERVED})
    demand_volume = sum(request.quantity_needed for request in relevant_requests if request.status in {RequestStatus.OPEN, RequestStatus.REQUESTED, RequestStatus.MATCHED, RequestStatus.RESERVED})
    demand_gap = 1 - _clamp(demand_volume / max(donation.quantity, demand_volume, 1))

    if freshness.final_status == "unsafe":
        expiry_pressure = 1.0
    elif freshness.time_left_hours <= 1.5:
        expiry_pressure = 0.88
    elif freshness.time_left_hours <= 3:
        expiry_pressure = 0.72
    elif freshness.time_left_hours <= 6:
        expiry_pressure = 0.52
    else:
        expiry_pressure = 0.24
    fit_gap = 1 - (best_match_fit / 100)
    activity_pressure = 0.15 if donation.status in {DonationStatus.RESERVED, DonationStatus.PICKED_UP} else 0.78 if matched_request_count == 0 else 0.38
    quantity_pressure = _clamp(donation.quantity / max(demand_volume, donation.quantity, 1))
    route_eta_pressure = 1.0 if ranked_matches and not feasible_matches else 0.0

    risk_score = round(
        (
            (0.43 * expiry_pressure)
            + (0.22 * fit_gap)
            + (0.17 * activity_pressure)
            + (0.1 * quantity_pressure)
            + (0.14 * max(demand_gap, route_eta_pressure))
        )
        * 100,
        1,
    )
    if donation.status in {DonationStatus.RESERVED, DonationStatus.PICKED_UP, DonationStatus.DELIVERED}:
        risk_score = max(round(risk_score - 28, 1), 6.0)

    if risk_score >= 70:
        risk_label = "high"
        recommended_action = "Prioritize immediately: route to the best-fit NGO and avoid holding this donation in queue."
    elif risk_score >= 40:
        risk_label = "medium"
        recommended_action = "Keep this donation near the top of the dispatch board and monitor approvals closely."
    else:
        risk_label = "low"
        recommended_action = "Current matching conditions are healthy; standard monitoring is enough."

    reasons = []
    if expiry_pressure >= 0.58:
        reasons.append(f"Only {freshness.time_left_hours} safe hours remain based on prepared time.")
    if best_match_fit < 70:
        reasons.append("Current NGO fit is weaker than the ideal rescue threshold.")
    if ranked_matches and not feasible_matches:
        reasons.append("Current travel ETA exceeds the remaining safe window for available NGO options.")
    if matched_request_count == 0:
        reasons.append("No live NGO request is attached to this donation yet.")
    if quantity_pressure > 0.7:
        reasons.append("Donation size is large relative to the active demand window.")
    if not reasons:
        reasons.append("This donation already has healthy demand and route feasibility.")

    return WasteRiskResult(
        donation_id=donation.id,
        risk_score=risk_score,
        risk_label=risk_label,
        final_status=freshness.final_status,
        top_reasons=reasons[:3],
        recommended_action=recommended_action,
        safe_hours_remaining=freshness.time_left_hours,
        best_match_fit=round(best_match_fit, 1),
    )
