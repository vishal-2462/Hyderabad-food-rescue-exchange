from __future__ import annotations

from app.config.freshness_categories import CATEGORY_KEYWORDS, FOOD_TYPE_TO_CATEGORY, FRESHNESS_CATEGORY_CONFIGS


def _normalize(value: str | None) -> str:
    return (value or "").strip().lower().replace("-", "_").replace(" ", "_")


def resolve_food_category(food_type: str | None, explicit_category: str | None = None, filename_hint: str | None = None, *, allow_unknown: bool = False) -> str:
    normalized_category = _normalize(explicit_category)
    if normalized_category in FRESHNESS_CATEGORY_CONFIGS:
        return normalized_category

    normalized_food_type = _normalize(food_type)
    if normalized_food_type in FOOD_TYPE_TO_CATEGORY:
        return FOOD_TYPE_TO_CATEGORY[normalized_food_type]

    hint = _normalize(filename_hint)
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword.replace(" ", "_") in hint for keyword in keywords):
            return category

    return "unknown" if allow_unknown else "biryani"


def route_visual_model(food_type: str | None, explicit_category: str | None = None, filename_hint: str | None = None) -> str:
    category = resolve_food_category(food_type, explicit_category, filename_hint, allow_unknown=True)
    return FRESHNESS_CATEGORY_CONFIGS[category].model_key
