from app.config.freshness_categories import FRESHNESS_CATEGORY_CONFIGS
from app.services.category_freshness import analyze_category_visual_signal, image_label_from_visual_label
from app.services.model_router import resolve_food_category, route_visual_model


def test_category_mapping_routes_food_types_into_specialized_groups() -> None:
    assert resolve_food_category("biryani") == "biryani"
    assert resolve_food_category("banana") == "fruit"
    assert resolve_food_category("naan") == "roti"
    assert resolve_food_category("chicken_curry") == "curry"


def test_category_specific_label_config_exists_for_required_groups() -> None:
    assert FRESHNESS_CATEGORY_CONFIGS["fruit"].visual_labels == ("fresh", "about_to_spoil", "spoiled")
    assert FRESHNESS_CATEGORY_CONFIGS["roti"].borderline_labels == ("dry_or_stale",)
    assert FRESHNESS_CATEGORY_CONFIGS["curry"].borderline_labels == ("oil_separated_or_stale",)


def test_category_visual_pipeline_detects_spoiled_fruit_conservatively() -> None:
    result = analyze_category_visual_signal(
        food_type="banana",
        explicit_category="fruit",
        filename="spoiled-banana.jpg",
        content_type="image/jpeg",
        byte_length=320_000,
    )

    assert result.food_category == "fruit"
    assert result.visual_label == "spoiled"
    assert result.visual_confidence >= 75
    assert image_label_from_visual_label(result.food_category, result.visual_label).value == "spoiled"


def test_model_router_exposes_category_specific_model_key() -> None:
    assert route_visual_model("banana", None, "banana.jpg") == "fruit-freshness-v1"
    assert route_visual_model("biryani", None, "biryani.jpg") == "biryani-freshness-v1"
