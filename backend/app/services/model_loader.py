from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.config.model_inference import MODEL_CHECKPOINT_PATH, MODEL_CLASS_MAP_PATH, MODEL_METADATA_PATH

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CategoryModelArtifacts:
    version: str
    trained_at: str
    model_path: Path
    metadata_path: Path
    class_map_path: Path
    output_dim: int
    num_classes: int
    class_names: tuple[str, ...]


def _load_json(path: Path):
    if not path.exists():
        raise RuntimeError(f"Required model artifact is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_class_names(class_names: list[str]) -> None:
    if not class_names:
        raise RuntimeError("Class map is empty.")
    if any(not name or not isinstance(name, str) for name in class_names):
        raise RuntimeError("Class map contains missing or invalid class names.")
    if len(set(class_names)) != len(class_names):
        raise RuntimeError("Class map contains duplicate class names.")


def _validate_metadata(metadata: dict[str, object]) -> None:
    required = ("version", "trained_at", "output_dim", "class_map_file", "checkpoint_file")
    missing = [key for key in required if key not in metadata]
    if missing:
        raise RuntimeError(f"Model metadata is missing required fields: {', '.join(missing)}")
    if str(metadata["class_map_file"]) != MODEL_CLASS_MAP_PATH.name:
        raise RuntimeError(
            f"Metadata class_map_file mismatch: expected {MODEL_CLASS_MAP_PATH.name}, got {metadata['class_map_file']}"
        )
    if str(metadata["checkpoint_file"]) != MODEL_CHECKPOINT_PATH.name:
        raise RuntimeError(
            f"Metadata checkpoint_file mismatch: expected {MODEL_CHECKPOINT_PATH.name}, got {metadata['checkpoint_file']}"
        )


@lru_cache(maxsize=1)
def load_category_model_artifacts() -> CategoryModelArtifacts:
    metadata = _load_json(MODEL_METADATA_PATH)
    if not isinstance(metadata, dict):
        raise RuntimeError("Metadata artifact must be a JSON object.")
    _validate_metadata(metadata)
    class_map_payload = _load_json(MODEL_CLASS_MAP_PATH)
    class_names = class_map_payload["class_names"] if isinstance(class_map_payload, dict) else class_map_payload
    if not isinstance(class_names, list):
        raise RuntimeError("Class map artifact must be a list or object with 'class_names'.")

    _validate_class_names(class_names)
    output_dim = int(metadata["output_dim"])
    num_classes = int(metadata.get("num_classes", output_dim))
    if output_dim != len(class_names) or num_classes != len(class_names):
        raise RuntimeError(
            f"Model output dimension mismatch: output_dim={output_dim}, num_classes={num_classes}, class_map={len(class_names)}"
        )
    if not MODEL_CHECKPOINT_PATH.exists():
        raise RuntimeError(f"Category classifier checkpoint is missing: {MODEL_CHECKPOINT_PATH}")

    artifacts = CategoryModelArtifacts(
        version=str(metadata["version"]),
        trained_at=str(metadata["trained_at"]),
        model_path=MODEL_CHECKPOINT_PATH,
        metadata_path=MODEL_METADATA_PATH,
        class_map_path=MODEL_CLASS_MAP_PATH,
        output_dim=output_dim,
        num_classes=num_classes,
        class_names=tuple(class_names),
    )
    logger.info("Loaded category model version=%s model_path=%s class_map_path=%s trained_at=%s classes=%s", artifacts.version, artifacts.model_path, artifacts.class_map_path, artifacts.trained_at, ",".join(artifacts.class_names))
    return artifacts


def validate_category_model_integrity() -> CategoryModelArtifacts:
    artifacts = load_category_model_artifacts()
    logger.info("Validated category model integrity version=%s output_dim=%s class_count=%s", artifacts.version, artifacts.output_dim, artifacts.num_classes)
    return artifacts
