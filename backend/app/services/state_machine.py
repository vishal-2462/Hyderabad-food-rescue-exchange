from __future__ import annotations

from typing import TypeVar

from app.models import DonationStatus, RequestStatus

StatusT = TypeVar("StatusT")


class InvalidTransitionError(ValueError):
    pass


DONATION_TRANSITIONS: dict[DonationStatus, set[DonationStatus]] = {
    DonationStatus.AVAILABLE: {
        DonationStatus.REQUESTED,
        DonationStatus.RESERVED,
        DonationStatus.CANCELLED,
        DonationStatus.EXPIRED,
    },
    DonationStatus.REQUESTED: {
        DonationStatus.AVAILABLE,
        DonationStatus.RESERVED,
        DonationStatus.CANCELLED,
        DonationStatus.EXPIRED,
    },
    DonationStatus.RESERVED: {
        DonationStatus.AVAILABLE,
        DonationStatus.PICKED_UP,
        DonationStatus.CANCELLED,
        DonationStatus.EXPIRED,
    },
    DonationStatus.PICKED_UP: {
        DonationStatus.DELIVERED,
        DonationStatus.CANCELLED,
    },
    DonationStatus.DELIVERED: set(),
    DonationStatus.EXPIRED: set(),
    DonationStatus.CANCELLED: set(),
}


REQUEST_TRANSITIONS: dict[RequestStatus, set[RequestStatus]] = {
    RequestStatus.OPEN: {
        RequestStatus.REQUESTED,
        RequestStatus.MATCHED,
        RequestStatus.RESERVED,
        RequestStatus.REJECTED,
        RequestStatus.CANCELLED,
        RequestStatus.EXPIRED,
    },
    RequestStatus.REQUESTED: {
        RequestStatus.RESERVED,
        RequestStatus.REJECTED,
        RequestStatus.CANCELLED,
        RequestStatus.EXPIRED,
    },
    RequestStatus.MATCHED: {
        RequestStatus.OPEN,
        RequestStatus.RESERVED,
        RequestStatus.REJECTED,
        RequestStatus.CANCELLED,
        RequestStatus.EXPIRED,
    },
    RequestStatus.RESERVED: {
        RequestStatus.OPEN,
        RequestStatus.FULFILLED,
        RequestStatus.CANCELLED,
        RequestStatus.EXPIRED,
    },
    RequestStatus.FULFILLED: set(),
    RequestStatus.REJECTED: set(),
    RequestStatus.EXPIRED: set(),
    RequestStatus.CANCELLED: set(),
}


def _assert_transition(
    mapping: dict[StatusT, set[StatusT]],
    current: StatusT,
    target: StatusT,
    label: str,
    *,
    allow_same_state: bool = True,
) -> None:
    if current == target:
        if allow_same_state:
            return
        allowed = mapping[current]
        allowed_values = ", ".join(item.value for item in sorted(allowed, key=lambda item: item.value)) or "no further transitions"
        raise InvalidTransitionError(
            f"Invalid {label} transition from '{current.value}' to '{target.value}'. Allowed: {allowed_values}."
        )
    allowed = mapping[current]
    if target not in allowed:
        allowed_values = ", ".join(item.value for item in sorted(allowed, key=lambda item: item.value)) or "no further transitions"
        raise InvalidTransitionError(
            f"Invalid {label} transition from '{current.value}' to '{target.value}'. Allowed: {allowed_values}."
        )


def assert_donation_transition(current: DonationStatus, target: DonationStatus, *, allow_same_state: bool = True) -> None:
    _assert_transition(DONATION_TRANSITIONS, current, target, "donation", allow_same_state=allow_same_state)


def assert_request_transition(current: RequestStatus, target: RequestStatus, *, allow_same_state: bool = True) -> None:
    _assert_transition(REQUEST_TRANSITIONS, current, target, "request", allow_same_state=allow_same_state)
