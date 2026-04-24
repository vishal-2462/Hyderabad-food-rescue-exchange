from app.store import reset_store
from app.services.ai_matching import rank_ai_matches


def test_ai_matching_returns_ranked_partner_with_reasoning() -> None:
    store = reset_store()
    donation = store.donations["donation-banjara-lunch"]

    ranked = rank_ai_matches(donation, list(store.requests.values()), store.ngos, store.donors)

    assert ranked
    assert ranked[0].ngo_name == "Seva Meals Hyderabad"
    assert ranked[0].fit_percentage > 70
    assert ranked[0].eta_minutes > 0
    assert ranked[0].time_left_hours > 0
    assert ranked[0].feasible is True
    assert ranked[0].reasons
    assert ranked[0].breakdown.urgency_fit >= 0
