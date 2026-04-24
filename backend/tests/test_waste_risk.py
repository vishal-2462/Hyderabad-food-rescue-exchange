from datetime import timedelta

from app.store import reset_store
from app.services.waste_risk import score_waste_risk


def test_waste_risk_identifies_time_sensitive_prepared_food() -> None:
    store = reset_store()
    donation = store.donations["donation-banjara-lunch"]
    donation.prepared_time = donation.prepared_time - timedelta(hours=2.5)

    risk = score_waste_risk(donation, list(store.requests.values()), store.ngos, store.donors)

    assert risk.risk_score > 0
    assert risk.risk_label in {"medium", "high"}
    assert risk.top_reasons
