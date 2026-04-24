from datetime import datetime, timedelta, timezone

import pytest

from app import schemas
from app.models import ImageFreshnessLabel
from app.services.freshness_engine import analyze_freshness, infer_shelf_life_hours


def test_prepared_time_is_required_for_donation_create_schema() -> None:
    with pytest.raises(Exception):
        schemas.DonationCreate(
            donor_id="donor-1",
            title="Fresh lunch",
            category="prepared_food",
            food_type="biryani",
            storage_condition="ambient",
            quantity=10,
            unit="meal_boxes",
            meals_estimate=10,
            pickup_start=datetime.now(timezone.utc),
            pickup_end=datetime.now(timezone.utc) + timedelta(hours=1),
            location={"area": "Ameerpet", "address": "addr", "city": "Hyderabad", "lat": 17.4, "lng": 78.4},
        )


def test_shelf_life_is_inferred_from_food_type() -> None:
    assert infer_shelf_life_hours("biryani", "ambient") == 5.0
    assert infer_shelf_life_hours("double_ka_meetha", "ambient") == 6.0


def test_expired_items_become_unsafe_from_time() -> None:
    now = datetime(2026, 4, 18, 15, 0, tzinfo=timezone.utc)
    assessment = analyze_freshness(
        food_type="biryani",
        prepared_time=now - timedelta(hours=6),
        current_time=now,
        storage_condition="ambient",
        quantity=20,
    )

    assert assessment.time_based_status == "unsafe"
    assert assessment.final_status == "unsafe"
    assert assessment.recommended_action == "Do not distribute"


def test_spoiled_image_cannot_override_expired_time() -> None:
    now = datetime(2026, 4, 18, 15, 0, tzinfo=timezone.utc)
    assessment = analyze_freshness(
        food_type="fried_rice",
        prepared_time=now - timedelta(hours=8),
        current_time=now,
        storage_condition="ambient",
        quantity=20,
        image_label=ImageFreshnessLabel.GOOD,
    )

    assert assessment.final_status == "unsafe"


def test_low_time_left_or_medium_image_marks_food_urgent() -> None:
    now = datetime(2026, 4, 18, 15, 0, tzinfo=timezone.utc)
    by_time = analyze_freshness(
        food_type="naan",
        prepared_time=now - timedelta(hours=2, minutes=20),
        current_time=now,
        storage_condition="ambient",
        quantity=12,
    )
    by_image = analyze_freshness(
        food_type="biryani",
        prepared_time=now - timedelta(hours=1),
        current_time=now,
        storage_condition="ambient",
        quantity=12,
        image_label=ImageFreshnessLabel.MEDIUM,
    )

    assert by_time.final_status == "urgent"
    assert by_image.final_status == "urgent"


def test_spoiled_visual_signal_with_high_confidence_marks_food_unsafe() -> None:
    now = datetime(2026, 4, 18, 15, 0, tzinfo=timezone.utc)
    assessment = analyze_freshness(
        food_type="fruit",
        prepared_time=now - timedelta(hours=1),
        current_time=now,
        storage_condition="ambient",
        quantity=5,
        visual_label="spoiled",
        visual_confidence=82.0,
    )

    assert assessment.final_status == "unsafe"
    assert assessment.food_category == "fruit"


def test_biryani_about_to_spoil_and_roti_stale_map_to_urgent_visual_status() -> None:
    now = datetime(2026, 4, 18, 15, 0, tzinfo=timezone.utc)
    biryani = analyze_freshness(
        food_type="biryani",
        prepared_time=now - timedelta(hours=1),
        current_time=now,
        storage_condition="ambient",
        quantity=10,
        visual_label="about_to_spoil",
        visual_confidence=69.0,
    )
    roti = analyze_freshness(
        food_type="naan",
        prepared_time=now - timedelta(minutes=30),
        current_time=now,
        storage_condition="ambient",
        quantity=10,
        visual_label="dry_or_stale",
        visual_confidence=66.0,
    )

    assert biryani.final_status == "urgent"
    assert roti.final_status == "urgent"


def test_unknown_category_can_still_be_unsafe_when_visual_spoilage_is_obvious() -> None:
    now = datetime(2026, 4, 18, 15, 0, tzinfo=timezone.utc)
    assessment = analyze_freshness(
        food_type="prepared_food",
        food_category="unknown",
        prepared_time=now - timedelta(hours=1),
        current_time=now,
        storage_condition="ambient",
        quantity=10,
        visual_label="spoiled",
        visual_confidence=82.0,
    )

    assert assessment.food_category == "unknown"
    assert assessment.final_status == "unsafe"


def test_expired_item_remains_unsafe_even_if_visual_signal_looks_fresh() -> None:
    now = datetime(2026, 4, 18, 15, 0, tzinfo=timezone.utc)
    assessment = analyze_freshness(
        food_type="fruit",
        prepared_time=now - timedelta(hours=10),
        current_time=now,
        storage_condition="ambient",
        quantity=10,
        visual_label="fresh",
        visual_confidence=91.0,
    )

    assert assessment.time_based_status == "unsafe"
    assert assessment.final_status == "unsafe"
