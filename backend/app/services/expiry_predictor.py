from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app import models
from app.models import Donation
from app.services.freshness_engine import analyze_donation_freshness, analyze_freshness


@dataclass(slots=True)
class ExpiryPrediction:
    estimated_safe_until: datetime
    remaining_safe_hours: float
    risk_level: str
    recommended_action: str
    explanation: str


def predict_food_expiry(
    *,
    category: str,
    prepared_at: datetime,
    storage_condition: str,
    packaging_type: str,
    ambient_temperature_c: float | None = None,
    existing_expires_at: datetime | None = None,
    now: datetime | None = None,
) -> ExpiryPrediction:
    image_label = None
    if packaging_type == "open_container":
        image_label = models.ImageFreshnessLabel.MEDIUM
    freshness = analyze_freshness(
        food_type=category,
        prepared_time=prepared_at,
        current_time=now,
        storage_condition=storage_condition,
        quantity=1,
        image_label=image_label,  # compatibility bridge for older callers
        shelf_life_hours=None,
    )
    risk_level = "high" if freshness.final_status == "unsafe" else "medium" if freshness.final_status == "urgent" else "low"
    return ExpiryPrediction(
        estimated_safe_until=freshness.safe_until,
        remaining_safe_hours=freshness.time_left_hours,
        risk_level=risk_level,
        recommended_action=freshness.recommended_action,
        explanation=freshness.explanation,
    )


def predict_expiry_for_donation(donation: Donation, *, now: datetime | None = None) -> ExpiryPrediction:
    freshness = analyze_donation_freshness(donation, current_time=now)
    risk_level = "high" if freshness.final_status == "unsafe" else "medium" if freshness.final_status == "urgent" else "low"
    return ExpiryPrediction(
        estimated_safe_until=freshness.safe_until,
        remaining_safe_hours=freshness.time_left_hours,
        risk_level=risk_level,
        recommended_action=freshness.recommended_action,
        explanation=freshness.explanation,
    )
