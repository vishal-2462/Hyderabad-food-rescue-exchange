from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class DonationStatus(str, Enum):
    AVAILABLE = "available"
    REQUESTED = "requested"
    RESERVED = "reserved"
    PICKED_UP = "picked_up"
    DELIVERED = "delivered"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class RequestStatus(str, Enum):
    OPEN = "open"
    REQUESTED = "requested"
    MATCHED = "matched"
    RESERVED = "reserved"
    FULFILLED = "fulfilled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class NotificationLevel(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"


class MealSlot(str, Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"


class ImageFreshnessLabel(str, Enum):
    GOOD = "good"
    MEDIUM = "medium"
    SPOILED = "spoiled"


class UserRole(str, Enum):
    DONOR = "donor"
    NGO = "ngo"


@dataclass(slots=True)
class Location:
    area: str
    address: str
    city: str
    lat: float
    lng: float


@dataclass(slots=True)
class Donor:
    id: str
    name: str
    phone: str
    donor_type: str
    reliability: int
    preferred_radius_km: float
    location: Location


@dataclass(slots=True)
class NGO:
    id: str
    name: str
    contact_name: str
    phone: str
    reliability: int
    max_daily_capacity: int
    current_load: int
    focus_areas: list[str] = field(default_factory=list)
    location: Location = field(default_factory=lambda: Location("", "", "", 0.0, 0.0))

    @property
    def remaining_capacity(self) -> int:
        return max(self.max_daily_capacity - self.current_load, 0)


@dataclass(slots=True)
class Donation:
    id: str
    donor_id: str
    title: str
    category: str
    food_type: str
    prepared_time: datetime
    storage_condition: str
    quantity: int
    unit: str
    meals_estimate: int
    safety_window_hours: int
    created_at: datetime
    expires_at: datetime
    pickup_start: datetime
    pickup_end: datetime
    status: DonationStatus
    location: Location
    shelf_life_hours: float | None = None
    image_url: str | None = None
    image_freshness_label: ImageFreshnessLabel | None = None
    image_visual_label: str | None = None
    image_visual_confidence: float | None = None
    notes: str = ""
    request_id: str | None = None
    reserved_for_request_id: str | None = None
    picked_up_at: datetime | None = None
    delivered_at: datetime | None = None


@dataclass(slots=True)
class Request:
    id: str
    ngo_id: str
    title: str
    category: str
    quantity_needed: int
    unit: str
    people_served: int
    priority: int
    created_at: datetime
    needed_by: datetime
    max_distance_km: float
    status: RequestStatus
    location: Location
    meal_slot: MealSlot | None = None
    notes: str = ""
    matched_donation_id: str | None = None


@dataclass(slots=True)
class Notification:
    id: str
    audience: str
    recipient_id: str | None
    title: str
    message: str
    level: NotificationLevel
    created_at: datetime
    read: bool = False


@dataclass(slots=True)
class User:
    id: str
    email: str
    password_hash: str
    role: UserRole
    profile_id: str | None
    created_at: datetime


@dataclass(slots=True)
class ImpactMetrics:
    snapshot_at: datetime
    total_donations: int
    active_donations: int
    delivered_donations: int
    total_quantity_kg: float
    meals_recovered: int
    co2e_avoided_kg: float
    open_requests: int
    fulfilled_requests: int
    donors_active: int
    ngos_active: int
    delivery_success_rate: float
