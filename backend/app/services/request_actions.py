from __future__ import annotations

from app import models
from app.services.state_machine import InvalidTransitionError, assert_donation_transition, assert_request_transition
from app.store import DataStore


def approve_request_with_donation(store: DataStore, request: models.Request, donation: models.Donation) -> None:
    if request.matched_donation_id is not None and request.matched_donation_id != donation.id:
        raise InvalidTransitionError("Request is already linked to a different donation.")

    if donation.request_id is not None and donation.request_id != request.id and donation.status != models.DonationStatus.AVAILABLE:
        raise InvalidTransitionError("Donation is already tied to another NGO request.")

    assert_request_transition(request.status, models.RequestStatus.RESERVED)
    assert_donation_transition(donation.status, models.DonationStatus.RESERVED)

    request.status = models.RequestStatus.RESERVED
    request.matched_donation_id = donation.id

    donation.status = models.DonationStatus.RESERVED
    donation.request_id = request.id
    donation.reserved_for_request_id = request.id


def reject_request(store: DataStore, request: models.Request) -> None:
    assert_request_transition(request.status, models.RequestStatus.REJECTED)
    request.status = models.RequestStatus.REJECTED

    if request.matched_donation_id is None:
        return

    donation = store.donations.get(request.matched_donation_id)
    if donation is None:
        return

    if donation.request_id == request.id and donation.status in {models.DonationStatus.REQUESTED, models.DonationStatus.RESERVED}:
        donation.status = models.DonationStatus.AVAILABLE
        donation.request_id = None
        donation.reserved_for_request_id = None
