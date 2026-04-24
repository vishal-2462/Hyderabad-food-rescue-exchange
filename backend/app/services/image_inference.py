from __future__ import annotations

from dataclasses import dataclass

from app.models import ImageFreshnessLabel
from app.services.category_classifier import CategoryCandidate, classify_food_category
from app.services.category_freshness import analyze_category_visual_signal


@dataclass(slots=True)
class FoodImageAnalysisResult:
    model_version: str
    food_type_guess: str
    food_category: str
    category_confidence: float
    confidence_bucket: str
    category_uncertain: bool
    uncertainty_reason: str | None
    top_categories: tuple[CategoryCandidate, ...]
    visual_label: str
    visual_confidence: float
    image_label: ImageFreshnessLabel
    quantity_estimate: str
    packaging_quality: str
    model_key: str
    suggested_storage: str
    distribution_urgency: str
    explanation: str
    debug_summary: str


KEYWORD_MAP = {
    "fruit": "Fruit batch",
    "banana": "Banana fruit",
    "apple": "Apple fruit",
    "biryani": "Biryani tray",
    "haleem": "Haleem pot",
    "roti": "Roti stack",
    "naan": "Naan stack",
    "curry": "Curry tray",
    "rice": "Rice tray",
    "fried": "Fried rice tray",
    "kebab": "Kebab tray",
    "meetha": "Dessert tray",
    "bread": "Bakery bread batch",
    "bun": "Bakery bun batch",
    "ration": "Dry ration pack",
}


def analyze_food_image(*, filename: str, content_type: str | None, byte_length: int) -> FoodImageAnalysisResult:
    lower_name = filename.lower()
    food_type_guess = "Mixed catering trays"
    for keyword, mapped in KEYWORD_MAP.items():
        if keyword in lower_name:
            food_type_guess = mapped
            break

    category_prediction = classify_food_category(
        food_type_hint=food_type_guess,
        filename=filename,
        content_type=content_type,
        byte_length=byte_length,
    )
    food_category = category_prediction.primary_category
    visual = analyze_category_visual_signal(
        food_type=food_type_guess,
        explicit_category=food_category,
        filename=filename,
        content_type=content_type,
        byte_length=byte_length,
    )

    if byte_length < 250_000:
        quantity_estimate = "single tray"
    elif byte_length < 1_000_000:
        quantity_estimate = "medium batch"
    else:
        quantity_estimate = "bulk catering batch"

    if "open" in lower_name:
        packaging_quality = "low"
    elif "box" in lower_name or "tray" in lower_name or "png" in lower_name or "jpg" in lower_name:
        packaging_quality = "high"
    else:
        packaging_quality = "medium"

    if food_category == "dry_rations":
        suggested_storage = "Keep sealed and dry; standard room storage is acceptable."
        distribution_urgency = "Distribute within the next 24 hours for best freshness."
    elif visual.image_label == ImageFreshnessLabel.SPOILED:
        suggested_storage = "Move into insulated or chilled storage immediately."
        distribution_urgency = "High urgency: prioritize same-day dispatch."
    elif visual.image_label == ImageFreshnessLabel.MEDIUM:
        suggested_storage = "Keep insulated or chilled and route quickly."
        distribution_urgency = "Urgent: pair with prepared-time analysis before dispatch."
    else:
        suggested_storage = "Keep sealed and avoid long ambient exposure."
        distribution_urgency = "Route within the next few hours."

    explanation = (
        f"The image analyzer routed this upload through model version '{category_prediction.model_version}'. "
        f"Predicted category is '{food_category}' with {category_prediction.primary_confidence:.2f} confidence bucket '{category_prediction.confidence_bucket}'. "
        f"Visual label '{visual.visual_label}' is a supporting signal only and should be combined with prepared time. "
        f"Detected content type: {content_type or 'unknown'} with an estimated {quantity_estimate} footprint."
    )
    if category_prediction.uncertain and category_prediction.uncertainty_reason:
        explanation = f"{explanation} Category uncertainty: {category_prediction.uncertainty_reason}"

    return FoodImageAnalysisResult(
        model_version=category_prediction.model_version,
        food_type_guess=food_type_guess,
        food_category=food_category,
        category_confidence=category_prediction.primary_confidence,
        confidence_bucket=category_prediction.confidence_bucket,
        category_uncertain=category_prediction.uncertain,
        uncertainty_reason=category_prediction.uncertainty_reason,
        top_categories=category_prediction.top_categories,
        visual_label=visual.visual_label,
        visual_confidence=visual.visual_confidence,
        image_label=visual.image_label,
        quantity_estimate=quantity_estimate,
        packaging_quality=packaging_quality,
        model_key=visual.model_key,
        suggested_storage=suggested_storage,
        distribution_urgency=distribution_urgency,
        explanation=f"{visual.explanation} {explanation}",
        debug_summary=category_prediction.debug_summary,
    )
