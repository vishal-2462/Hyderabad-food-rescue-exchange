from app.store import reset_store
from app.services.route_optimizer import optimize_route


def test_route_optimizer_returns_eta_and_stops() -> None:
    store = reset_store()
    donation = store.donations["donation-banjara-lunch"]
    requests = [store.requests["request-seva-breakfast"], store.requests["request-charminar-lunch"]]

    route = optimize_route(donation, requests, store.ngos, store.donors)

    assert route.total_eta_minutes > 0
    assert route.total_distance_km > 0
    assert route.stops
    assert route.stops[0].ngo_name == "Seva Meals Hyderabad"
