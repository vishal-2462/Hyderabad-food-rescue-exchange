from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FreshnessCategoryConfig:
    category: str
    visual_labels: tuple[str, ...]
    borderline_labels: tuple[str, ...]
    spoiled_labels: tuple[str, ...]
    model_key: str
    default_shelf_life_hours_by_storage: dict[str, float]
    label_explanations: dict[str, str]
    spoiled_confidence_threshold: float = 68.0


FRESHNESS_CATEGORY_CONFIGS: dict[str, FreshnessCategoryConfig] = {
    "unknown": FreshnessCategoryConfig(
        category="unknown",
        visual_labels=("visually_uncertain", "about_to_spoil", "spoiled"),
        borderline_labels=("visually_uncertain", "about_to_spoil"),
        spoiled_labels=("spoiled",),
        model_key="unknown-freshness-v1",
        default_shelf_life_hours_by_storage={"ambient": 6.0, "insulated": 6.0, "chilled": 6.0, "frozen": 6.0},
        label_explanations={
            "visually_uncertain": "The image does not confidently match a trained food category.",
            "about_to_spoil": "The image is ambiguous but shows borderline deterioration cues.",
            "spoiled": "Strong spoilage cues were detected despite category uncertainty.",
        },
    ),
    "fruit": FreshnessCategoryConfig(
        category="fruit",
        visual_labels=("fresh", "about_to_spoil", "spoiled"),
        borderline_labels=("about_to_spoil",),
        spoiled_labels=("spoiled",),
        model_key="fruit-freshness-v1",
        default_shelf_life_hours_by_storage={"ambient": 8.0, "insulated": 8.5, "chilled": 12.0, "frozen": 20.0},
        label_explanations={
            "fresh": "Fruit looks intact and suitable for short-horizon distribution.",
            "about_to_spoil": "Fruit shows overripe or bruising cues and should be prioritized quickly.",
            "spoiled": "Fruit shows decay or mold-like cues and should not be distributed.",
        },
    ),
    "biryani": FreshnessCategoryConfig(
        category="biryani",
        visual_labels=("fresh", "about_to_spoil", "spoiled"),
        borderline_labels=("about_to_spoil",),
        spoiled_labels=("spoiled",),
        model_key="biryani-freshness-v1",
        default_shelf_life_hours_by_storage={"ambient": 5.0, "insulated": 5.4, "chilled": 6.1, "frozen": 7.5},
        label_explanations={
            "fresh": "Rice and garnish structure still look serviceable for near-term rescue.",
            "about_to_spoil": "Biryani appears borderline and should move only on urgent routes.",
            "spoiled": "Visual spoilage cues suggest the biryani should not be redistributed.",
        },
    ),
    "roti": FreshnessCategoryConfig(
        category="roti",
        visual_labels=("fresh", "dry_or_stale", "spoiled"),
        borderline_labels=("dry_or_stale",),
        spoiled_labels=("spoiled",),
        model_key="roti-freshness-v1",
        default_shelf_life_hours_by_storage={"ambient": 3.5, "insulated": 4.0, "chilled": 5.0, "frozen": 7.0},
        label_explanations={
            "fresh": "Flatbread texture appears usable for immediate rescue.",
            "dry_or_stale": "Roti looks dry or stale and should be treated as urgent.",
            "spoiled": "Roti shows contamination or spoilage cues and should not be distributed.",
        },
    ),
    "curry": FreshnessCategoryConfig(
        category="curry",
        visual_labels=("fresh", "oil_separated_or_stale", "spoiled"),
        borderline_labels=("oil_separated_or_stale",),
        spoiled_labels=("spoiled",),
        model_key="curry-freshness-v1",
        default_shelf_life_hours_by_storage={"ambient": 5.0, "insulated": 5.3, "chilled": 6.2, "frozen": 7.5},
        label_explanations={
            "fresh": "Curry texture looks stable enough for quick delivery.",
            "oil_separated_or_stale": "Oil separation or stale cues suggest the curry is becoming risky.",
            "spoiled": "The curry appears spoiled and should not be distributed.",
        },
    ),
    "rice": FreshnessCategoryConfig(
        category="rice",
        visual_labels=("fresh", "about_to_spoil", "spoiled"),
        borderline_labels=("about_to_spoil",),
        spoiled_labels=("spoiled",),
        model_key="rice-freshness-v1",
        default_shelf_life_hours_by_storage={"ambient": 5.0, "insulated": 5.2, "chilled": 6.0, "frozen": 7.0},
        label_explanations={
            "fresh": "Rice grains appear recently prepared and still suitable for rescue.",
            "about_to_spoil": "Rice looks borderline and should be routed immediately.",
            "spoiled": "Rice spoilage cues were detected.",
        },
    ),
    "kebab": FreshnessCategoryConfig(
        category="kebab",
        visual_labels=("fresh", "about_to_spoil", "spoiled"),
        borderline_labels=("about_to_spoil",),
        spoiled_labels=("spoiled",),
        model_key="kebab-freshness-v1",
        default_shelf_life_hours_by_storage={"ambient": 4.0, "insulated": 4.3, "chilled": 5.2, "frozen": 6.0},
        label_explanations={
            "fresh": "Kebabs still look suitable for short-horizon rescue.",
            "about_to_spoil": "Kebabs appear dry or old and should be prioritized quickly.",
            "spoiled": "The kebabs visually appear spoiled.",
        },
    ),
    "dessert": FreshnessCategoryConfig(
        category="dessert",
        visual_labels=("fresh", "about_to_spoil", "spoiled"),
        borderline_labels=("about_to_spoil",),
        spoiled_labels=("spoiled",),
        model_key="dessert-freshness-v1",
        default_shelf_life_hours_by_storage={"ambient": 6.0, "insulated": 6.4, "chilled": 8.0, "frozen": 10.0},
        label_explanations={
            "fresh": "Dessert still looks serviceable for immediate rescue.",
            "about_to_spoil": "Dessert is softening or separating and should be treated as urgent.",
            "spoiled": "Dessert looks spoiled and should not be distributed.",
        },
    ),
    "fried_rice": FreshnessCategoryConfig(
        category="fried_rice",
        visual_labels=("fresh", "about_to_spoil", "spoiled"),
        borderline_labels=("about_to_spoil",),
        spoiled_labels=("spoiled",),
        model_key="fried-rice-freshness-v1",
        default_shelf_life_hours_by_storage={"ambient": 5.0, "insulated": 5.3, "chilled": 6.0, "frozen": 7.0},
        label_explanations={
            "fresh": "Fried rice still looks acceptable for fast redistribution.",
            "about_to_spoil": "Fried rice appears borderline and should move immediately.",
            "spoiled": "Fried rice spoilage cues were detected.",
        },
    ),
    "haleem": FreshnessCategoryConfig(
        category="haleem",
        visual_labels=("fresh", "about_to_spoil", "spoiled"),
        borderline_labels=("about_to_spoil",),
        spoiled_labels=("spoiled",),
        model_key="haleem-freshness-v1",
        default_shelf_life_hours_by_storage={"ambient": 3.0, "insulated": 3.3, "chilled": 4.0, "frozen": 5.0},
        label_explanations={
            "fresh": "Haleem texture still looks fit for urgent same-day delivery.",
            "about_to_spoil": "Haleem appears borderline and is running out of safe time.",
            "spoiled": "Haleem visually appears spoiled and unsafe.",
        },
    ),
    "bread_or_bakery": FreshnessCategoryConfig(
        category="bread_or_bakery",
        visual_labels=("fresh", "dry_or_stale", "spoiled"),
        borderline_labels=("dry_or_stale",),
        spoiled_labels=("spoiled",),
        model_key="bakery-freshness-v1",
        default_shelf_life_hours_by_storage={"ambient": 12.0, "insulated": 12.5, "chilled": 16.0, "frozen": 24.0},
        label_explanations={
            "fresh": "Bakery texture still looks serviceable.",
            "dry_or_stale": "Bread or bakery appears stale and should be treated cautiously.",
            "spoiled": "Bakery spoilage cues were detected.",
        },
    ),
    "dry_rations": FreshnessCategoryConfig(
        category="dry_rations",
        visual_labels=("fresh", "about_to_spoil", "spoiled"),
        borderline_labels=("about_to_spoil",),
        spoiled_labels=("spoiled",),
        model_key="dry-rations-freshness-v1",
        default_shelf_life_hours_by_storage={"ambient": 72.0, "insulated": 72.0, "chilled": 72.0, "frozen": 72.0},
        label_explanations={
            "fresh": "Dry ration packaging appears intact.",
            "about_to_spoil": "Dry ration packaging looks compromised and needs review.",
            "spoiled": "Dry ration spoilage or packaging failure cues were detected.",
        },
    ),
}


FOOD_TYPE_TO_CATEGORY: dict[str, str] = {
    "biryani": "biryani",
    "fruit": "fruit",
    "banana": "fruit",
    "apple": "fruit",
    "orange": "fruit",
    "mango": "fruit",
    "roti": "roti",
    "chapati": "roti",
    "naan": "roti",
    "chicken_curry": "curry",
    "curry": "curry",
    "dal": "curry",
    "rice": "rice",
    "fried_rice": "fried_rice",
    "kebab": "kebab",
    "dessert": "dessert",
    "double_ka_meetha": "dessert",
    "haleem": "haleem",
    "bread": "bread_or_bakery",
    "bread_or_bakery": "bread_or_bakery",
    "bakery": "bread_or_bakery",
    "bun": "bread_or_bakery",
    "pastry": "bread_or_bakery",
    "prepared_food": "biryani",
    "dry_rations": "dry_rations",
}


CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "unknown": tuple(),
    "fruit": ("fruit", "banana", "apple", "orange", "mango", "grape", "papaya", "watermelon"),
    "biryani": ("biryani",),
    "roti": ("roti", "chapati", "naan", "paratha"),
    "curry": ("curry", "dal", "gravy"),
    "rice": ("rice",),
    "kebab": ("kebab", "tikka"),
    "dessert": ("dessert", "meetha", "halwa", "sweet"),
    "fried_rice": ("fried_rice", "fried-rice", "fried rice"),
    "haleem": ("haleem",),
    "bread_or_bakery": ("bread", "bakery", "bun", "pastry", "cake"),
    "dry_rations": ("ration", "dry", "grain", "lentil"),
}
