from __future__ import annotations

from dataclasses import dataclass

from app import models
from app.config.freshness_categories import FRESHNESS_CATEGORY_CONFIGS
from app.services.model_router import resolve_food_category, route_visual_model


@dataclass(slots=True)
class CategoryVisualResult:
    food_category: str
    visual_label: str
    visual_confidence: float
    image_label: models.ImageFreshnessLabel
    explanation: str
    model_key: str


VISUAL_CUES: dict[str, dict[str, tuple[str, ...]]] = {
    "fruit": {
        "spoiled": ("spoiled", "rotten", "mold", "fungus", "black", "decay"),
        "borderline": ("overripe", "bruised", "soft", "brown", "wrinkled"),
        "fresh": ("fresh", "ripe", "whole", "clean"),
    },
    "roti": {
        "spoiled": ("mold", "spoiled", "fungus"),
        "borderline": ("dry", "stale", "hard"),
        "fresh": ("fresh", "soft", "warm"),
    },
    "curry": {
        "spoiled": ("spoiled", "sour", "mold"),
        "borderline": ("oil_separated", "separated", "stale", "split"),
        "fresh": ("fresh", "packed", "sealed"),
    },
    "bread_or_bakery": {
        "spoiled": ("mold", "spoiled"),
        "borderline": ("dry", "stale", "old"),
        "fresh": ("fresh", "soft", "packed"),
    },
}

GLOBAL_VISUAL_CUES = {
    "spoiled": ("spoiled", "rotten", "mold", "moldy", "fungus", "decay", "black_spots"),
    "borderline": ("stale", "dry", "wrinkled", "bruised", "soft"),
}


def _default_borderline_label(food_category: str) -> str:
    config = FRESHNESS_CATEGORY_CONFIGS[food_category]
    return config.borderline_labels[0] if config.borderline_labels else config.visual_labels[1]


def image_label_from_visual_label(food_category: str, visual_label: str) -> models.ImageFreshnessLabel:
    config = FRESHNESS_CATEGORY_CONFIGS[food_category]
    if visual_label in config.spoiled_labels:
        return models.ImageFreshnessLabel.SPOILED
    if visual_label in config.borderline_labels:
        return models.ImageFreshnessLabel.MEDIUM
    if visual_label == "fresh":
        return models.ImageFreshnessLabel.GOOD
    return models.ImageFreshnessLabel.MEDIUM


def visual_status_from_label(food_category: str, visual_label: str) -> str:
    generic = image_label_from_visual_label(food_category, visual_label)
    if generic == models.ImageFreshnessLabel.SPOILED:
        return "unsafe"
    if generic == models.ImageFreshnessLabel.MEDIUM:
        return "urgent"
    return "safe"


def category_visual_result_from_generic(food_category: str, generic_label: models.ImageFreshnessLabel | None, visual_confidence: float | None = None) -> tuple[str | None, float | None]:
    if generic_label is None:
        return None, visual_confidence

    if food_category == "unknown" and generic_label == models.ImageFreshnessLabel.GOOD:
        return "visually_uncertain", visual_confidence if visual_confidence is not None else 52.0
    if generic_label == models.ImageFreshnessLabel.GOOD:
        return "fresh", visual_confidence if visual_confidence is not None else 64.0
    if generic_label == models.ImageFreshnessLabel.MEDIUM:
        return _default_borderline_label(food_category), visual_confidence if visual_confidence is not None else 66.0
    return "spoiled", visual_confidence if visual_confidence is not None else 78.0


def analyze_category_visual_signal(
    *,
    food_type: str | None,
    explicit_category: str | None,
    filename: str,
    content_type: str | None,
    byte_length: int,
) -> CategoryVisualResult:
    lower_name = filename.lower()
    food_category = resolve_food_category(food_type, explicit_category, lower_name, allow_unknown=True)
    config = FRESHNESS_CATEGORY_CONFIGS[food_category]
    cues = VISUAL_CUES.get(food_category, {})
    model_key = route_visual_model(food_type, explicit_category, lower_name)

    if any(token in lower_name for token in GLOBAL_VISUAL_CUES["spoiled"]) or any(token in lower_name for token in cues.get("spoiled", ())):
        visual_label = "spoiled"
        visual_confidence = 84.0 if food_category == "unknown" else 82.0
    elif any(token in lower_name for token in GLOBAL_VISUAL_CUES["borderline"]) or any(token in lower_name for token in cues.get("borderline", ())):
        visual_label = _default_borderline_label(food_category)
        visual_confidence = 66.0 if food_category == "unknown" else 69.0
    elif any(token in lower_name for token in cues.get("fresh", ())):
        visual_label = "fresh"
        visual_confidence = 68.0 if byte_length < 1_000_000 else 74.0
    elif food_category == "unknown":
        visual_label = "visually_uncertain"
        visual_confidence = 44.0
    elif byte_length < 200_000:
        visual_label = _default_borderline_label(food_category)
        visual_confidence = 61.0
    else:
        visual_label = _default_borderline_label(food_category)
        visual_confidence = 58.0

    image_label = image_label_from_visual_label(food_category, visual_label)
    label_explanation = config.label_explanations.get(visual_label, "Category-aware visual freshness routing is active.")
    explanation = (
        f"Stage 1 routed the upload to the '{food_category}' freshness pipeline using model key '{model_key}'. "
        f"Stage 2 assigned visual label '{visual_label}' with {visual_confidence:.0f}% visual confidence. {label_explanation} "
        f"Content type: {content_type or 'unknown'}; byte size: {byte_length}."
    )

    return CategoryVisualResult(
        food_category=food_category,
        visual_label=visual_label,
        visual_confidence=visual_confidence,
        image_label=image_label,
        explanation=explanation,
        model_key=model_key,
    )
