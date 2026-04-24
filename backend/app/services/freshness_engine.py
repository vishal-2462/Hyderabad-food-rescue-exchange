from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging

from app import models
from app.config.freshness_categories import FRESHNESS_CATEGORY_CONFIGS
from app.services.category_freshness import category_visual_result_from_generic, image_label_from_visual_label, visual_status_from_label
from app.services.model_loader import load_category_model_artifacts
from app.services.model_router import resolve_food_category

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class FreshnessAssessment:
    model_version: str | None
    food_category: str
    category_confidence: float | None
    confidence_bucket: str | None
    category_uncertain: bool
    uncertainty_reason: str | None
    top_categories: tuple[object, ...]
    shelf_life_hours: float
    time_elapsed_hours: float
    time_left_hours: float
    safe_until: datetime
    visual_label: str | None
    visual_confidence: float | None
    time_based_status: str
    final_status: str
    urgency_status: str
    recommended_action: str
    explanation: str
    image_label: models.ImageFreshnessLabel | None
    debug_summary: str | None


def infer_shelf_life_hours(food_type: str, storage_condition: str, shelf_life_hours: float | None = None, food_category: str | None = None) -> float:
    resolved_category = resolve_food_category(food_type, food_category)
    config = FRESHNESS_CATEGORY_CONFIGS[resolved_category]
    base_shelf_life = shelf_life_hours if shelf_life_hours is not None else config.default_shelf_life_hours_by_storage.get(storage_condition, config.default_shelf_life_hours_by_storage["ambient"])
    return round(base_shelf_life, 2)


def base_risk_from_time(time_left_hours: float) -> str:
    if time_left_hours <= 0:
        return "unsafe"
    if time_left_hours <= 1.5:
        return "urgent"
    return "safe"


def final_freshness_decision(
    *,
    food_category: str,
    time_left_hours: float,
    visual_label: str | None,
    visual_confidence: float | None,
) -> tuple[str, str, str]:
    time_based_status = base_risk_from_time(time_left_hours)
    if time_based_status == "unsafe":
        return time_based_status, "blocked", "Do not distribute"

    if visual_label is not None:
        visual_status = visual_status_from_label(food_category, visual_label)
        spoiled_threshold = FRESHNESS_CATEGORY_CONFIGS[food_category].spoiled_confidence_threshold
        if visual_status == "unsafe" and (visual_confidence or 0) >= spoiled_threshold:
            return "unsafe", "blocked", "Do not distribute"
        if time_left_hours <= 1.5 or visual_status == "urgent":
            return "urgent", "deliver_immediately", "Deliver immediately / prioritize nearest NGO"

    if time_left_hours <= 1.5:
        return "urgent", "deliver_immediately", "Deliver immediately / prioritize nearest NGO"
    return "safe", "normal", "Standard distribution"


def _resolve_visual_signal(
    *,
    food_category: str,
    visual_label: str | None,
    visual_confidence: float | None,
    image_label: models.ImageFreshnessLabel | None,
) -> tuple[str | None, float | None, models.ImageFreshnessLabel | None]:
    if visual_label is not None:
        return visual_label, visual_confidence if visual_confidence is not None else 64.0, image_label_from_visual_label(food_category, visual_label)

    derived_label, derived_confidence = category_visual_result_from_generic(food_category, image_label, visual_confidence)
    return derived_label, derived_confidence, image_label


def analyze_freshness(
    *,
    food_type: str,
    food_category: str | None = None,
    prepared_time: datetime,
    current_time: datetime | None = None,
    storage_condition: str,
    quantity: int,
    image_label: models.ImageFreshnessLabel | None = None,
    visual_label: str | None = None,
    visual_confidence: float | None = None,
    category_confidence: float | None = None,
    confidence_bucket: str | None = None,
    category_uncertain: bool = False,
    uncertainty_reason: str | None = None,
    top_categories: tuple[object, ...] = (),
    model_version: str | None = None,
    debug_summary: str | None = None,
    shelf_life_hours: float | None = None,
) -> FreshnessAssessment:
    reference_time = current_time or datetime.now(timezone.utc)
    resolved_food_category = resolve_food_category(food_type, food_category)
    resolved_shelf_life = infer_shelf_life_hours(food_type, storage_condition, shelf_life_hours, resolved_food_category)
    safe_until = prepared_time + timedelta(hours=resolved_shelf_life)
    time_elapsed_hours = round((reference_time - prepared_time).total_seconds() / 3600, 2)
    time_left_hours = round((safe_until - reference_time).total_seconds() / 3600, 2)
    time_based_status = base_risk_from_time(time_left_hours)
    resolved_visual_label, resolved_visual_confidence, resolved_image_label = _resolve_visual_signal(
        food_category=resolved_food_category,
        visual_label=visual_label,
        visual_confidence=visual_confidence,
        image_label=image_label,
    )
    spoilage_override_triggered = False
    if resolved_visual_label is not None:
        visual_status = visual_status_from_label(resolved_food_category, resolved_visual_label)
        if visual_status == "unsafe" and (resolved_visual_confidence or 0) >= FRESHNESS_CATEGORY_CONFIGS[resolved_food_category].spoiled_confidence_threshold and time_based_status != "unsafe":
            spoilage_override_triggered = True
    final_status, urgency_status, recommended_action = final_freshness_decision(
        food_category=resolved_food_category,
        time_left_hours=time_left_hours,
        visual_label=resolved_visual_label,
        visual_confidence=resolved_visual_confidence,
    )

    explanation_parts = [
        f"Prepared {max(time_elapsed_hours, 0):.2f}h ago.",
        f"Food category '{resolved_food_category.replace('_', ' ')}' gives an effective shelf life of {resolved_shelf_life:.2f}h under {storage_condition.replace('_', ' ')} storage.",
        f"Remaining safe time is {time_left_hours:.2f}h.",
        f"Time-based status is '{time_based_status}'.",
    ]
    if resolved_visual_label is not None:
        explanation_parts.append(
            f"Visual state is '{resolved_visual_label}' at {resolved_visual_confidence or 0:.0f}% confidence and is treated only as a supporting signal."
        )
    explanation_parts.append(f"Quantity {quantity} does not change freshness directly but affects urgency once routing begins.")
    explanation_parts.append(f"Final decision is '{final_status}' because time of preparation overrides uncertain image cues.")
    if category_uncertain:
        explanation_parts.append(f"Category uncertainty note: {uncertainty_reason}")
    computed_debug_summary = debug_summary or (
        f"food_category={resolved_food_category} time_based_status={time_based_status} final_status={final_status} "
        f"spoilage_override_triggered={spoilage_override_triggered}"
    )
    logger.info(
        "Freshness diagnostics food_category=%s time_based_status=%s final_status=%s time_left_hours=%.2f visual_label=%s visual_confidence=%s category_uncertain=%s spoilage_override_triggered=%s",
        resolved_food_category,
        time_based_status,
        final_status,
        time_left_hours,
        resolved_visual_label,
        resolved_visual_confidence,
        category_uncertain,
        spoilage_override_triggered,
    )

    return FreshnessAssessment(
        model_version=model_version,
        food_category=resolved_food_category,
        category_confidence=category_confidence,
        confidence_bucket=confidence_bucket,
        category_uncertain=category_uncertain,
        uncertainty_reason=uncertainty_reason,
        top_categories=top_categories,
        shelf_life_hours=resolved_shelf_life,
        time_elapsed_hours=time_elapsed_hours,
        time_left_hours=time_left_hours,
        safe_until=safe_until,
        visual_label=resolved_visual_label,
        visual_confidence=resolved_visual_confidence,
        time_based_status=time_based_status,
        final_status=final_status,
        urgency_status=urgency_status,
        recommended_action=recommended_action,
        explanation=" ".join(explanation_parts),
        image_label=resolved_image_label,
        debug_summary=computed_debug_summary,
    )


def analyze_donation_freshness(donation: models.Donation, *, current_time: datetime | None = None) -> FreshnessAssessment:
    model_version = None
    if donation.image_visual_label is not None or donation.image_freshness_label is not None:
        model_version = load_category_model_artifacts().version
    return analyze_freshness(
        food_type=donation.food_type,
        food_category=None,
        prepared_time=donation.prepared_time,
        current_time=current_time,
        storage_condition=donation.storage_condition,
        quantity=donation.quantity,
        image_label=donation.image_freshness_label,
        visual_label=donation.image_visual_label,
        visual_confidence=donation.image_visual_confidence,
        model_version=model_version,
        shelf_life_hours=donation.shelf_life_hours,
    )


def delivery_feasibility(*, eta_minutes: int, time_left_hours: float, final_status: str) -> tuple[bool, str]:
    if final_status == "unsafe" or time_left_hours <= 0:
        return False, "Not feasible: donation is already outside the safe time window."
    if (eta_minutes / 60) > time_left_hours:
        return False, "Not feasible: estimated travel time exceeds remaining safe window."
    return True, "Feasible: estimated travel time fits within the remaining safe window."
