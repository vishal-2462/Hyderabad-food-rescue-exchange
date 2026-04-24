from __future__ import annotations

from dataclasses import dataclass

from app.models import Donation, DonationStatus, Donor, NGO, Request
from app.services.ai_matching import rank_ai_matches
from app.services.impact_analytics import summarize_impact_intelligence
from app.services.route_optimizer import optimize_route
from app.services.waste_risk import score_waste_risk


@dataclass(slots=True)
class AssistantResponse:
    answer: str
    bullet_points: list[str]
    follow_up_prompts: list[str]
    cited_entity_ids: list[str]


def _active_donations(donations: list[Donation]) -> list[Donation]:
    return [donation for donation in donations if donation.status in {DonationStatus.AVAILABLE, DonationStatus.REQUESTED, DonationStatus.RESERVED, DonationStatus.PICKED_UP}]


def _top_priority_donation(donations: list[Donation], requests: list[Request], ngos_by_id: dict[str, NGO], donors_by_id: dict[str, Donor]) -> tuple[Donation | None, object | None]:
    scored = [(donation, score_waste_risk(donation, requests, ngos_by_id, donors_by_id)) for donation in _active_donations(donations)]
    if not scored:
        return None, None
    donation, risk = max(scored, key=lambda item: item[1].risk_score)
    return donation, risk


def answer_question(
    question: str,
    donations: list[Donation],
    requests: list[Request],
    donors: list[Donor],
    ngos: list[NGO],
) -> AssistantResponse:
    lower_question = question.lower()
    donors_by_id = {donor.id: donor for donor in donors}
    ngos_by_id = {ngo.id: ngo for ngo in ngos}
    priority_donation, priority_risk = _top_priority_donation(donations, requests, ngos_by_id, donors_by_id)

    if ("priorit" in lower_question or "urgent" in lower_question) and priority_donation is not None and priority_risk is not None:
        matches = rank_ai_matches(priority_donation, requests, ngos_by_id, donors_by_id)
        best_match = matches[0] if matches else None
        answer = f"Prioritize {priority_donation.title}: it carries a {priority_risk.risk_label} waste risk at {priority_risk.risk_score:.0f}/100."
        bullet_points = [
            f"Safe window remaining: {priority_risk.safe_hours_remaining} hours.",
            f"Best NGO fit: {best_match.ngo_name} at {best_match.fit_percentage:.1f}% fit." if best_match else "No strong NGO fit is currently available.",
            priority_risk.recommended_action,
        ]
        return AssistantResponse(
            answer=answer,
            bullet_points=bullet_points,
            follow_up_prompts=["Which NGO is best for this donation?", "Show me the fastest route", "What is the overall waste risk today?"],
            cited_entity_ids=[priority_donation.id] + ([best_match.ngo_id] if best_match else []),
        )

    if ("best ngo" in lower_question or "best match" in lower_question or "which ngo" in lower_question) and priority_donation is not None:
        matches = rank_ai_matches(priority_donation, requests, ngos_by_id, donors_by_id)
        best_match = matches[0] if matches else None
        if best_match is None:
            return AssistantResponse(
                answer="No viable NGO match is available right now.",
                bullet_points=["The current request pool does not align strongly with the selected donation profile."],
                follow_up_prompts=["Which donation should be prioritized today?", "What is the waste risk today?", "How many meals did we save?"],
                cited_entity_ids=[priority_donation.id],
            )

        return AssistantResponse(
            answer=f"{best_match.ngo_name} is the best NGO for {priority_donation.title} with a {best_match.fit_percentage:.1f}% fit.",
            bullet_points=best_match.reasons + [f"Confidence: {best_match.confidence_percentage:.1f}%.", best_match.explanation],
            follow_up_prompts=["Show me the fastest route", "Why is this donation urgent?", "How many meals did we save?"],
            cited_entity_ids=[priority_donation.id, best_match.ngo_id, best_match.request_id],
        )

    if "route" in lower_question or "eta" in lower_question:
        if priority_donation is None:
            return AssistantResponse(
                answer="No active donation is available for route planning right now.",
                bullet_points=["Create or select a live donation to get a logistics recommendation."],
                follow_up_prompts=["Which donation should be prioritized today?", "Which NGO is best for this donation?", "What is the waste risk today?"],
                cited_entity_ids=[],
            )

        route = optimize_route(priority_donation, requests, ngos_by_id, donors_by_id)
        if not route.stops:
            return AssistantResponse(
                answer=f"I don't have a route recommendation for {priority_donation.title} yet.",
                bullet_points=["There are no compatible NGO requests in the current board."],
                follow_up_prompts=["Which NGO is best for this donation?", "What is the waste risk today?", "How many meals did we save?"],
                cited_entity_ids=[priority_donation.id],
            )

        return AssistantResponse(
            answer=f"The fastest delivery suggestion is to start with {route.stops[0].ngo_name} and reach it in about {route.stops[0].cumulative_eta_minutes} minutes.",
            bullet_points=[
                f"Total route distance: {route.total_distance_km} km.",
                f"Stops in order: {', '.join(stop.ngo_name for stop in route.stops)}.",
                route.summary,
            ],
            follow_up_prompts=["Which NGO is best for this donation?", "What is the overall waste risk today?", "How many meals did we save?"],
            cited_entity_ids=[priority_donation.id] + [stop.ngo_id for stop in route.stops],
        )

    if "waste" in lower_question or "risk" in lower_question:
        scored = [score_waste_risk(donation, requests, ngos_by_id, donors_by_id) for donation in _active_donations(donations)]
        high_risk = [risk for risk in scored if risk.risk_label == "high"]
        medium_risk = [risk for risk in scored if risk.risk_label == "medium"]
        return AssistantResponse(
            answer=f"The board currently has {len(high_risk)} high-risk and {len(medium_risk)} medium-risk donations.",
            bullet_points=[
                f"Highest risk score on the board: {max((risk.risk_score for risk in scored), default=0):.0f}/100.",
                priority_risk.recommended_action if priority_risk is not None else "No immediate action is required.",
                "Prepared food with low safe hours should be approved before routing lower-risk stock.",
            ],
            follow_up_prompts=["Which donation should be prioritized today?", "Show me the fastest route", "How many meals did we save?"],
            cited_entity_ids=[risk.donation_id for risk in high_risk[:3]],
        )

    summary = summarize_impact_intelligence(donations, requests, donors, ngos)
    return AssistantResponse(
        answer=f"The platform has already saved {summary.meals_saved_this_week} meals and is on track for about {summary.expected_meals_next_week} next week.",
        bullet_points=summary.explanation,
        follow_up_prompts=["Which donation should be prioritized today?", "Which NGO is best for this donation?", "What is the waste risk today?"],
        cited_entity_ids=[item.actor_id for item in [summary.top_donor, summary.top_ngo] if item is not None],
    )
