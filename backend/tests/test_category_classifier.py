from app.services.category_classifier import classify_food_category


def test_low_confidence_sample_becomes_unknown() -> None:
    prediction = classify_food_category(food_type_hint=None, filename="meal-tray.jpg", content_type="image/jpeg", byte_length=300_000)

    assert prediction.primary_category == "unknown"
    assert len(prediction.top_categories) == 3
    assert prediction.uncertain is True


def test_close_top_categories_trigger_unknown_margin_guard() -> None:
    prediction = classify_food_category(food_type_hint=None, filename="banana-bread.jpg", content_type="image/jpeg", byte_length=420_000)

    assert prediction.primary_category == "unknown"
    assert prediction.uncertain is True
    assert prediction.uncertainty_reason is not None
    assert "margin" in prediction.uncertainty_reason.lower() or "threshold" in prediction.uncertainty_reason.lower()


def test_moldy_bakery_like_image_does_not_collapse_into_biryani() -> None:
    prediction = classify_food_category(food_type_hint=None, filename="moldy-bread.jpg", content_type="image/jpeg", byte_length=350_000)

    assert prediction.primary_category in {"bread_or_bakery", "unknown"}
    assert prediction.top_categories[0].label != "biryani" or prediction.primary_category == "unknown"
