from datetime import datetime, timezone

from fastapi import APIRouter

from app import models, schemas
from app.services.impact import aggregate_impact
from app.services.matching import rank_matches
from app.store import get_store

router = APIRouter(prefix="/admin", tags=["admin"])


def _serialize_match(result) -> schemas.MatchCandidate:
    return schemas.MatchCandidate(
        request_id=result.request_id,
        ngo_id=result.ngo_id,
        request_title=result.request_title,
        ngo_name=result.ngo_name,
        total_score=result.total_score,
        distance_km=result.distance_km,
        factor_scores=schemas.MatchFactorScores(
            distance=result.factor_scores.distance,
            expiry_urgency=result.factor_scores.expiry_urgency,
            safety_window=result.factor_scores.safety_window,
            capacity=result.factor_scores.capacity,
            demand=result.factor_scores.demand,
            reliability=result.factor_scores.reliability,
        ),
        explanation=result.explanation,
    )


@router.get("/overview", response_model=schemas.AdminOverview)
def get_admin_overview() -> schemas.AdminOverview:
    store = get_store()
    now = datetime.now(timezone.utc)
    expiring_donations = [
        donation
        for donation in store.donations.values()
        if donation.status in {models.DonationStatus.AVAILABLE, models.DonationStatus.REQUESTED, models.DonationStatus.RESERVED}
        and (donation.expires_at - now).total_seconds() <= 6 * 3600
    ]

    top_matches: list[schemas.MatchCandidate] = []
    for donation in expiring_donations[:3]:
        ranked = rank_matches(donation, list(store.requests.values()), store.ngos, store.donors, now=now)
        if ranked:
            top_matches.append(_serialize_match(ranked[0]))

    impact = aggregate_impact(
        list(store.donations.values()),
        list(store.requests.values()),
        list(store.donors.values()),
        list(store.ngos.values()),
        snapshot_at=now,
    )

    notifications = sorted(store.notifications.values(), key=lambda item: item.created_at, reverse=True)
    return schemas.AdminOverview(
        snapshot_at=now,
        donor_count=len(store.donors),
        ngo_count=len(store.ngos),
        donation_count=len(store.donations),
        open_request_count=sum(
            1
            for request in store.requests.values()
            if request.status in {models.RequestStatus.OPEN, models.RequestStatus.REQUESTED, models.RequestStatus.MATCHED, models.RequestStatus.RESERVED}
        ),
        reserved_donation_count=sum(1 for donation in store.donations.values() if donation.status == models.DonationStatus.RESERVED),
        expiring_donations=[schemas.Donation.model_validate(donation) for donation in expiring_donations],
        notifications=[schemas.Notification.model_validate(notification) for notification in notifications[:6]],
        top_matches=top_matches,
        impact=schemas.ImpactMetrics.model_validate(impact),
    )
