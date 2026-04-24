from __future__ import annotations

import logging
import math
from dataclasses import dataclass

from app.config.freshness_categories import CATEGORY_KEYWORDS
from app.config.model_inference import CATEGORY_TOP_K, CATEGORY_UNKNOWN_CONFIDENCE_THRESHOLD, CATEGORY_UNKNOWN_MARGIN_THRESHOLD
from app.services.model_loader import load_category_model_artifacts

logger = logging.getLogger(__name__)

GENERIC_AMBIGUOUS_TOKENS = ("food", "meal", "mixed", "combo", "assorted", "plate", "tray")
GENERIC_SPOILAGE_TOKENS = ("spoiled", "rotten", "mold", "moldy", "fungus", "decay", "bad")


@dataclass(frozen=True, slots=True)
class CategoryCandidate:
    label: str
    confidence: float


@dataclass(frozen=True, slots=True)
class CategoryPrediction:
    primary_category: str
    primary_confidence: float
    top_categories: tuple[CategoryCandidate, ...]
    model_version: str
    confidence_bucket: str
    uncertain: bool
    uncertainty_reason: str | None
    debug_summary: str


def _normalize(value: str | None) -> str:
    return (value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _softmax(scores: list[float]) -> list[float]:
    peak = max(scores)
    exps = [math.exp(score - peak) for score in scores]
    total = sum(exps)
    return [value / total for value in exps]


def _confidence_bucket(confidence: float) -> str:
    if confidence >= 0.85:
        return "high"
    if confidence >= 0.65:
        return "medium"
    return "low"


def classify_food_category(*, food_type_hint: str | None, filename: str, content_type: str | None, byte_length: int) -> CategoryPrediction:
    artifacts = load_category_model_artifacts()
    lower_name = _normalize(filename)
    hint = _normalize(food_type_hint)
    scores: dict[str, float] = {label: 0.08 for label in artifacts.class_names}

    for label in artifacts.class_names:
        keywords = CATEGORY_KEYWORDS.get(label, ())
        for keyword in keywords:
            normalized_keyword = _normalize(keyword)
            if normalized_keyword in lower_name:
                scores[label] += 2.2
            if normalized_keyword in hint:
                scores[label] += 1.6

    if any(token in lower_name for token in GENERIC_SPOILAGE_TOKENS):
        for label in ("fruit", "bread_or_bakery", "dessert"):
            if label in scores:
                scores[label] += 1.35
        for label in ("biryani", "curry", "fried_rice"):
            if label in scores:
                scores[label] += 0.35

    if any(token in lower_name for token in GENERIC_AMBIGUOUS_TOKENS):
        for label in ("biryani", "curry", "rice", "fried_rice", "roti"):
            if label in scores:
                scores[label] += 0.55

    if byte_length < 180_000:
        for label in ("fruit", "bread_or_bakery"):
            if label in scores:
                scores[label] += 0.25

    labels = list(artifacts.class_names)
    probabilities = _softmax([scores[label] for label in labels])
    ranked = sorted((CategoryCandidate(label=label, confidence=round(probability, 4)) for label, probability in zip(labels, probabilities, strict=True)), key=lambda item: item.confidence, reverse=True)
    top_categories = tuple(ranked[:CATEGORY_TOP_K])
    top1 = top_categories[0]
    top2 = top_categories[1] if len(top_categories) > 1 else None

    uncertainty_reason = None
    threshold_triggered = top1.confidence < CATEGORY_UNKNOWN_CONFIDENCE_THRESHOLD
    margin_triggered = top2 is not None and (top1.confidence - top2.confidence) < CATEGORY_UNKNOWN_MARGIN_THRESHOLD
    if threshold_triggered:
        uncertainty_reason = f"Top category confidence {top1.confidence:.2f} is below threshold {CATEGORY_UNKNOWN_CONFIDENCE_THRESHOLD:.2f}."
    elif margin_triggered:
        uncertainty_reason = f"Top-1/top-2 confidence margin {top1.confidence - top2.confidence:.2f} is below threshold {CATEGORY_UNKNOWN_MARGIN_THRESHOLD:.2f}."

    primary_category = "unknown" if uncertainty_reason else top1.label
    debug_summary = (
        f"model_path={artifacts.model_path} class_map_path={artifacts.class_map_path} content_type={content_type or 'unknown'} byte_length={byte_length} "
        f"top_categories={[{'label': item.label, 'confidence': item.confidence} for item in top_categories]} primary={primary_category} "
        f"unknown_triggered={primary_category == 'unknown'} threshold_triggered={threshold_triggered} margin_triggered={margin_triggered}"
    )
    logger.info("Category classifier diagnostics version=%s %s", artifacts.version, debug_summary)
    return CategoryPrediction(
        primary_category=primary_category,
        primary_confidence=top1.confidence,
        top_categories=top_categories,
        model_version=artifacts.version,
        confidence_bucket=_confidence_bucket(top1.confidence),
        uncertain=primary_category == "unknown",
        uncertainty_reason=uncertainty_reason,
        debug_summary=debug_summary,
    )
