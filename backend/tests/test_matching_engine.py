from datetime import datetime, timedelta, timezone

from app.models import Donation, DonationStatus, Donor, NGO, Location, Request, RequestStatus
from app.services.matching import rank_matches


def test_matching_engine_prioritizes_nearby_urgent_request_with_capacity() -> None:
    now = datetime(2026, 4, 17, 9, 0, tzinfo=timezone.utc)

    donor = Donor(
        id="donor-1",
        name="Test Donor",
        phone="1",
        donor_type="kitchen",
        reliability=90,
        preferred_radius_km=20,
        location=Location("Banjara Hills", "", "Hyderabad", 17.4126, 78.4380),
    )
    ngo_near = NGO(
        id="ngo-near",
        name="Nearby NGO",
        contact_name="A",
        phone="1",
        reliability=92,
        max_daily_capacity=120,
        current_load=10,
        focus_areas=["prepared_food"],
        location=Location("Jubilee Hills", "", "Hyderabad", 17.4307, 78.4035),
    )
    ngo_far = NGO(
        id="ngo-far",
        name="Far NGO",
        contact_name="B",
        phone="2",
        reliability=80,
        max_daily_capacity=80,
        current_load=60,
        focus_areas=["prepared_food"],
        location=Location("LB Nagar", "", "Hyderabad", 17.3457, 78.5520),
    )
    donation = Donation(
        id="don-1",
        donor_id=donor.id,
        title="Meal boxes",
        category="prepared_food",
        food_type="biryani",
        prepared_time=now - timedelta(hours=1, minutes=30),
        storage_condition="ambient",
        quantity=70,
        unit="meal_boxes",
        meals_estimate=70,
        safety_window_hours=2,
        created_at=now - timedelta(hours=1),
        expires_at=now + timedelta(hours=5),
        pickup_start=now + timedelta(minutes=30),
        pickup_end=now + timedelta(hours=2),
        status=DonationStatus.AVAILABLE,
        location=donor.location,
        shelf_life_hours=None,
        image_url=None,
        image_freshness_label=None,
    )
    request_near = Request(
        id="req-near",
        ngo_id=ngo_near.id,
        title="Urgent breakfast round",
        category="prepared_food",
        quantity_needed=65,
        unit="meal_boxes",
        people_served=65,
        priority=5,
        created_at=now - timedelta(hours=1),
        needed_by=now + timedelta(hours=4),
        max_distance_km=15,
        status=RequestStatus.OPEN,
        location=ngo_near.location,
    )
    request_far = Request(
        id="req-far",
        ngo_id=ngo_far.id,
        title="Evening meal stock",
        category="prepared_food",
        quantity_needed=70,
        unit="meal_boxes",
        people_served=70,
        priority=3,
        created_at=now - timedelta(hours=1),
        needed_by=now + timedelta(hours=10),
        max_distance_km=30,
        status=RequestStatus.OPEN,
        location=ngo_far.location,
    )

    ranked = rank_matches(
        donation,
        [request_far, request_near],
        {ngo_near.id: ngo_near, ngo_far.id: ngo_far},
        {donor.id: donor},
        now=now,
    )

    assert ranked[0].request_id == request_near.id
    assert ranked[0].factor_scores.distance > ranked[1].factor_scores.distance
    assert ranked[0].factor_scores.capacity > ranked[1].factor_scores.capacity


def test_matching_engine_penalizes_candidates_that_break_safety_window() -> None:
    now = datetime(2026, 4, 17, 9, 0, tzinfo=timezone.utc)

    donor = Donor(
        id="donor-1",
        name="Test Donor",
        phone="1",
        donor_type="kitchen",
        reliability=90,
        preferred_radius_km=20,
        location=Location("Ameerpet", "", "Hyderabad", 17.4375, 78.4483),
    )
    ngo = NGO(
        id="ngo-1",
        name="Safe NGO",
        contact_name="A",
        phone="1",
        reliability=90,
        max_daily_capacity=100,
        current_load=0,
        focus_areas=["prepared_food"],
        location=Location("Madhapur", "", "Hyderabad", 17.4504, 78.3820),
    )
    donation = Donation(
        id="don-1",
        donor_id=donor.id,
        title="Meal boxes",
        category="prepared_food",
        food_type="fried_rice",
        prepared_time=now,
        storage_condition="ambient",
        quantity=40,
        unit="meal_boxes",
        meals_estimate=40,
        safety_window_hours=3,
        created_at=now,
        expires_at=now + timedelta(hours=4),
        pickup_start=now,
        pickup_end=now + timedelta(hours=1),
        status=DonationStatus.AVAILABLE,
        location=donor.location,
        shelf_life_hours=None,
        image_url=None,
        image_freshness_label=None,
    )
    impossible = Request(
        id="req-impossible",
        ngo_id=ngo.id,
        title="Too late to use",
        category="prepared_food",
        quantity_needed=40,
        unit="meal_boxes",
        people_served=40,
        priority=5,
        created_at=now,
        needed_by=now + timedelta(hours=5),
        max_distance_km=30,
        status=RequestStatus.OPEN,
        location=Location("Shamshabad", "", "Hyderabad", 17.2403, 78.4294),
    )

    ranked = rank_matches(donation, [impossible], {ngo.id: ngo}, {donor.id: donor}, now=now)

    assert ranked[0].factor_scores.safety_window == 0.0
    assert ranked[0].total_score < 30
