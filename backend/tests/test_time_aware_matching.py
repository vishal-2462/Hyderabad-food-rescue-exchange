from datetime import datetime, timedelta, timezone

from app.models import Donation, DonationStatus, Donor, NGO, Location, Request, RequestStatus
from app.services.ai_matching import rank_ai_matches


def test_matching_marks_far_ngo_infeasible_when_eta_exceeds_time_left() -> None:
    now = datetime(2026, 4, 18, 12, 0, tzinfo=timezone.utc)
    donor = Donor(
        id="donor-1",
        name="Test Donor",
        phone="1",
        donor_type="kitchen",
        reliability=90,
        preferred_radius_km=20,
        location=Location("Ameerpet", "", "Hyderabad", 17.4375, 78.4483),
    )
    ngo_near = NGO(
        id="ngo-near",
        name="Near NGO",
        contact_name="Near",
        phone="1",
        reliability=90,
        max_daily_capacity=120,
        current_load=10,
        focus_areas=["prepared_food"],
        location=Location("Panjagutta", "", "Hyderabad", 17.4330, 78.4500),
    )
    ngo_far = NGO(
        id="ngo-far",
        name="Far NGO",
        contact_name="Far",
        phone="2",
        reliability=92,
        max_daily_capacity=120,
        current_load=10,
        focus_areas=["prepared_food"],
        location=Location("Shamshabad", "", "Hyderabad", 17.2403, 78.4294),
    )
    donation = Donation(
        id="donation-1",
        donor_id=donor.id,
        title="Late lunch",
        category="prepared_food",
        food_type="biryani",
        prepared_time=now - timedelta(hours=4.2),
        storage_condition="ambient",
        quantity=40,
        unit="meal_boxes",
        meals_estimate=40,
        safety_window_hours=2,
        created_at=now - timedelta(hours=4),
        expires_at=now + timedelta(minutes=40),
        pickup_start=now,
        pickup_end=now + timedelta(minutes=30),
        status=DonationStatus.AVAILABLE,
        location=donor.location,
        shelf_life_hours=None,
        image_url=None,
        image_freshness_label=None,
    )
    near_request = Request(
        id="request-near",
        ngo_id=ngo_near.id,
        title="Near request",
        category="prepared_food",
        quantity_needed=35,
        unit="meal_boxes",
        people_served=35,
        priority=5,
        created_at=now,
        needed_by=now + timedelta(hours=1),
        max_distance_km=15,
        status=RequestStatus.OPEN,
        location=ngo_near.location,
    )
    far_request = Request(
        id="request-far",
        ngo_id=ngo_far.id,
        title="Far request",
        category="prepared_food",
        quantity_needed=35,
        unit="meal_boxes",
        people_served=35,
        priority=5,
        created_at=now,
        needed_by=now + timedelta(hours=1),
        max_distance_km=40,
        status=RequestStatus.OPEN,
        location=ngo_far.location,
    )

    ranked = rank_ai_matches(donation, [far_request, near_request], {ngo_near.id: ngo_near, ngo_far.id: ngo_far}, {donor.id: donor}, now=now)

    assert ranked[0].ngo_id == ngo_near.id
    assert ranked[0].feasible is True
    assert any(match.ngo_id == ngo_far.id and match.feasible is False for match in ranked)
    assert any("remaining safe window" in match.feasibility_reason for match in ranked if match.ngo_id == ngo_far.id)
