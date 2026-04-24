from datetime import datetime, timedelta, timezone

from app.services.expiry_predictor import predict_food_expiry


def test_expiry_predictor_flags_hot_ambient_food_as_time_sensitive() -> None:
    prepared_at = datetime.now(timezone.utc) - timedelta(hours=4)

    prediction = predict_food_expiry(
        category="prepared_food",
        prepared_at=prepared_at,
        storage_condition="ambient",
        packaging_type="open_container",
        ambient_temperature_c=35,
    )

    assert prediction.risk_level == "medium"
    assert prediction.remaining_safe_hours <= 2
    assert "Food category" in prediction.explanation
