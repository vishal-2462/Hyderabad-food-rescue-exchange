from datetime import datetime, timezone

from fastapi import HTTPException

from app import schemas
from app.auth_store import get_user_store
from app.api.routers.requests import create_request
from app.models import DonationStatus, RequestStatus, User, UserRole
from app.store import get_store, reset_store


def test_create_request_from_donation_marks_donation_requested_and_links_request() -> None:
    reset_store()
    ngo_user = get_user_store().get_by_email("ngo@example.com")
    assert ngo_user is not None

    created = create_request(
        schemas.DonationRequestCreate(
            donation_id="donation-banjara-lunch",
            ngo_id="ngo-seva-meals",
        ),
        current_user=ngo_user,
    )
    store = get_store()
    donation = store.donations["donation-banjara-lunch"]

    assert created.status == RequestStatus.REQUESTED
    assert created.matched_donation_id == donation.id
    assert donation.status == DonationStatus.REQUESTED
    assert donation.request_id == created.id
    assert donation.reserved_for_request_id is None


def test_create_request_from_non_available_donation_respects_state_machine() -> None:
    reset_store()
    ngo_user = get_user_store().get_by_email("ngo@example.com")
    assert ngo_user is not None

    try:
        create_request(
            schemas.DonationRequestCreate(
                donation_id="donation-banjara-delivered",
                ngo_id="ngo-seva-meals",
            ),
            current_user=ngo_user,
        )
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "Invalid donation transition" in str(exc.detail)
    else:
        raise AssertionError("Expected HTTPException for invalid donation request transition")


def test_create_request_from_already_requested_donation_is_rejected() -> None:
    reset_store()
    ngo_user = get_user_store().get_by_email("ngo@example.com")
    assert ngo_user is not None
    second_ngo_user = User(
        id="user-test-charminar",
        email="charminar@example.com",
        password_hash="test",
        role=UserRole.NGO,
        profile_id="ngo-charminar-shelter",
        created_at=datetime.now(timezone.utc),
    )

    create_request(
        schemas.DonationRequestCreate(
            donation_id="donation-banjara-lunch",
            ngo_id="ngo-seva-meals",
        ),
        current_user=ngo_user,
    )

    try:
        create_request(
            schemas.DonationRequestCreate(
                donation_id="donation-banjara-lunch",
                ngo_id="ngo-charminar-shelter",
            ),
            current_user=second_ngo_user,
        )
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "Invalid donation transition" in str(exc.detail)
    else:
        raise AssertionError("Expected HTTPException for duplicate donation request")
