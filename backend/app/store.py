from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.data.seed import build_demo_seed
from app.models import Donation, Donor, NGO, Notification, NotificationLevel, Request


class DataStore:
    def __init__(
        self,
        donors: list[Donor] | None = None,
        ngos: list[NGO] | None = None,
        donations: list[Donation] | None = None,
        requests: list[Request] | None = None,
        notifications: list[Notification] | None = None,
    ) -> None:
        self.donors = {donor.id: donor for donor in donors or []}
        self.ngos = {ngo.id: ngo for ngo in ngos or []}
        self.donations = {donation.id: donation for donation in donations or []}
        self.requests = {request.id: request for request in requests or []}
        self.notifications = {notification.id: notification for notification in notifications or []}

    @classmethod
    def with_demo_data(cls) -> "DataStore":
        donors, ngos, donations, requests, notifications = build_demo_seed()
        return cls(donors=donors, ngos=ngos, donations=donations, requests=requests, notifications=notifications)

    def new_id(self, prefix: str) -> str:
        return f"{prefix}-{uuid4().hex[:8]}"

    def add_donation(self, donation: Donation) -> Donation:
        self.donations[donation.id] = donation
        return donation

    def add_donor(self, donor: Donor) -> Donor:
        self.donors[donor.id] = donor
        return donor

    def add_ngo(self, ngo: NGO) -> NGO:
        self.ngos[ngo.id] = ngo
        return ngo

    def add_request(self, request: Request) -> Request:
        self.requests[request.id] = request
        return request

    def add_notification(
        self,
        audience: str,
        title: str,
        message: str,
        *,
        recipient_id: str | None = None,
        level: NotificationLevel = NotificationLevel.INFO,
    ) -> Notification:
        notification = Notification(
            id=self.new_id("notification"),
            audience=audience,
            recipient_id=recipient_id,
            title=title,
            message=message,
            level=level,
            created_at=datetime.now(timezone.utc),
        )
        self.notifications[notification.id] = notification
        return notification


_store: DataStore | None = None


def get_store() -> DataStore:
    global _store
    if _store is None:
        _store = DataStore.with_demo_data()
    return _store


def reset_store() -> DataStore:
    global _store
    _store = DataStore.with_demo_data()
    return _store
