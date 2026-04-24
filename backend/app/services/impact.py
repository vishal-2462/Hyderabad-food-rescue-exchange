from __future__ import annotations

from datetime import datetime, timezone

from app.models import Donation, DonationStatus, Donor, ImpactMetrics, NGO, Request, RequestStatus


ACTIVE_DONATION_STATES = {
    DonationStatus.AVAILABLE,
    DonationStatus.REQUESTED,
    DonationStatus.RESERVED,
    DonationStatus.PICKED_UP,
}


def aggregate_impact(
    donations: list[Donation],
    requests: list[Request],
    donors: list[Donor],
    ngos: list[NGO],
    snapshot_at: datetime | None = None,
) -> ImpactMetrics:
    reference_time = snapshot_at or datetime.now(timezone.utc)
    delivered = [donation for donation in donations if donation.status == DonationStatus.DELIVERED]
    active = [donation for donation in donations if donation.status in ACTIVE_DONATION_STATES]
    fulfilled_requests = [request for request in requests if request.status == RequestStatus.FULFILLED]

    meals_recovered = sum(donation.meals_estimate for donation in delivered)
    total_quantity_kg = round(sum(donation.quantity for donation in delivered), 1)
    completed_outcomes = [donation for donation in donations if donation.status in {DonationStatus.DELIVERED, DonationStatus.CANCELLED, DonationStatus.EXPIRED}]
    delivery_success_rate = 0.0
    if completed_outcomes:
        delivered_count = sum(1 for donation in completed_outcomes if donation.status == DonationStatus.DELIVERED)
        delivery_success_rate = round((delivered_count / len(completed_outcomes)) * 100, 1)

    return ImpactMetrics(
        snapshot_at=reference_time,
        total_donations=len(donations),
        active_donations=len(active),
        delivered_donations=len(delivered),
        total_quantity_kg=total_quantity_kg,
        meals_recovered=meals_recovered,
        co2e_avoided_kg=round(total_quantity_kg * 2.5, 1),
        open_requests=sum(1 for request in requests if request.status in {RequestStatus.OPEN, RequestStatus.REQUESTED, RequestStatus.MATCHED, RequestStatus.RESERVED}),
        fulfilled_requests=len(fulfilled_requests),
        donors_active=len({donation.donor_id for donation in donations}) or len(donors),
        ngos_active=len({request.ngo_id for request in requests}) or len(ngos),
        delivery_success_rate=delivery_success_rate,
    )
