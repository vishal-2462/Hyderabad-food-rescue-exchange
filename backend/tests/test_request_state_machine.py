import pytest

from app.models import DonationStatus, RequestStatus
from app.services.state_machine import InvalidTransitionError, assert_donation_transition, assert_request_transition


def test_request_state_machine_allows_open_to_fulfilled_path() -> None:
    assert_request_transition(RequestStatus.OPEN, RequestStatus.MATCHED)
    assert_request_transition(RequestStatus.REQUESTED, RequestStatus.RESERVED)
    assert_request_transition(RequestStatus.MATCHED, RequestStatus.RESERVED)
    assert_request_transition(RequestStatus.RESERVED, RequestStatus.FULFILLED)


def test_request_state_machine_blocks_reopening_fulfilled_request() -> None:
    with pytest.raises(InvalidTransitionError):
        assert_request_transition(RequestStatus.FULFILLED, RequestStatus.OPEN)


def test_donation_state_machine_allows_available_to_requested_and_reserved() -> None:
    assert_donation_transition(DonationStatus.AVAILABLE, DonationStatus.REQUESTED)
    assert_donation_transition(DonationStatus.REQUESTED, DonationStatus.RESERVED)


def test_donation_state_machine_blocks_requesting_delivered_donation() -> None:
    with pytest.raises(InvalidTransitionError):
        assert_donation_transition(DonationStatus.DELIVERED, DonationStatus.REQUESTED)


def test_donation_state_machine_can_block_same_state_transition_when_needed() -> None:
    with pytest.raises(InvalidTransitionError):
        assert_donation_transition(DonationStatus.REQUESTED, DonationStatus.REQUESTED, allow_same_state=False)
