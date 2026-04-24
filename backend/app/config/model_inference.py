from __future__ import annotations

import os
from pathlib import Path


MODEL_VERSION = os.getenv("AI_CATEGORY_MODEL_VERSION", "freshness-category-v2")
MODEL_ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "model_artifacts" / MODEL_VERSION
MODEL_METADATA_PATH = MODEL_ARTIFACT_DIR / "metadata.json"
MODEL_CLASS_MAP_PATH = MODEL_ARTIFACT_DIR / "class_names.json"
MODEL_CHECKPOINT_PATH = MODEL_ARTIFACT_DIR / "checkpoint.mock"

CATEGORY_UNKNOWN_CONFIDENCE_THRESHOLD = float(os.getenv("AI_CATEGORY_UNKNOWN_CONFIDENCE_THRESHOLD", "0.75"))
CATEGORY_UNKNOWN_MARGIN_THRESHOLD = float(os.getenv("AI_CATEGORY_UNKNOWN_MARGIN_THRESHOLD", "0.10"))
CATEGORY_TOP_K = int(os.getenv("AI_CATEGORY_TOP_K", "3"))
