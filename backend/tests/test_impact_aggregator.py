from datetime import datetime, timedelta, timezone

from app.models import Donation, DonationStatus, Donor, NGO, Location, Request, RequestStatus
from app.services.impact import aggregate_impact


def test_impact_aggregator_summarizes_delivery_and_recovery_metrics() -> None:
    now = datetime(2026, 4, 17, 9, 0, tzinfo=timezone.utc)
    donor = Donor(
        id="donor-1",
        name="Donor",
        phone="1",
        donor_type="kitchen",
        reliability=90,
        preferred_radius_km=10,
        location=Location("Ameerpet", "", "Hyderabad", 17.4375, 78.4483),
    )
    ngo = NGO(
        id="ngo-1",
        name="NGO",
        contact_name="Person",
        phone="2",
        reliability=88,
        max_daily_capacity=200,
        current_load=0,
        focus_areas=["prepared_food"],
        location=Location("Jubilee Hills", "", "Hyderabad", 17.4307, 78.4035),
    )
    delivered = Donation(
        id="delivered",
        donor_id=donor.id,
        title="Delivered food",
        category="prepared_food",
        food_type="biryani",
        prepared_time=now - timedelta(days=1, hours=2),
        storage_condition="ambient",
        quantity=50,
        unit="meal_boxes",
        meals_estimate=50,
        safety_window_hours=2,
        created_at=now - timedelta(days=1),
        expires_at=now - timedelta(hours=10),
        pickup_start=now - timedelta(days=1),
        pickup_end=now - timedelta(days=1, minutes=-30),
        status=DonationStatus.DELIVERED,
        location=donor.location,
        shelf_life_hours=None,
        image_url=None,
        image_freshness_label=None,
        delivered_at=now - timedelta(hours=12),
    )
    active = Donation(
        id="active",
        donor_id=donor.id,
        title="Active food",
        category="prepared_food",
        food_type="chicken_curry",
        prepared_time=now - timedelta(hours=1),
        storage_condition="ambient",
        quantity=30,
        unit="meal_boxes",
        meals_estimate=30,
        safety_window_hours=2,
        created_at=now,
        expires_at=now + timedelta(hours=6),
        pickup_start=now,
        pickup_end=now + timedelta(hours=1),
        status=DonationStatus.AVAILABLE,
        location=donor.location,
        shelf_life_hours=None,
        image_url=None,
        image_freshness_label=None,
    )
    request_open = Request(
        id="req-open",
        ngo_id=ngo.id,
        title="Open request",
        category="prepared_food",
        quantity_needed=30,
        unit="meal_boxes",
        people_served=30,
        priority=4,
        created_at=now,
        needed_by=now + timedelta(hours=4),
        max_distance_km=10,
        status=RequestStatus.OPEN,
        location=ngo.location,
    )
    request_done = Request(
        id="req-done",
        ngo_id=ngo.id,
        title="Done request",
        category="prepared_food",
        quantity_needed=50,
        unit="meal_boxes",
        people_served=50,
        priority=5,
        created_at=now - timedelta(days=1),
        needed_by=now - timedelta(hours=12),
        max_distance_km=10,
        status=RequestStatus.FULFILLED,
        location=ngo.location,
    )

    metrics = aggregate_impact([delivered, active], [request_open, request_done], [donor], [ngo], snapshot_at=now)

    assert metrics.total_donations == 2
    assert metrics.active_donations == 1
    assert metrics.delivered_donations == 1
    assert metrics.meals_recovered == 50
    assert metrics.total_quantity_kg == 50
    assert metrics.co2e_avoided_kg == 125.0
    assert metrics.open_requests == 1
    assert metrics.fulfilled_requests == 1
    assert metrics.delivery_success_rate == 100.0
