from __future__ import annotations

import json

import pytest

from app.services import model_loader


def test_model_loader_reads_explicit_class_map(tmp_path, monkeypatch) -> None:
    metadata_path = tmp_path / "metadata.json"
    class_map_path = tmp_path / "class_names.json"
    checkpoint_path = tmp_path / "checkpoint.mock"
    metadata_path.write_text(
        json.dumps(
            {
                "version": "test-v1",
                "trained_at": "2026-04-18T09:00:00Z",
                "output_dim": 3,
                "num_classes": 3,
                "class_map_file": "class_names.json",
                "checkpoint_file": "checkpoint.mock",
            }
        ),
        encoding="utf-8",
    )
    class_map_path.write_text(json.dumps({"class_names": ["fruit", "bread_or_bakery", "biryani"]}), encoding="utf-8")
    checkpoint_path.write_text("checkpoint", encoding="utf-8")

    monkeypatch.setattr(model_loader, "MODEL_METADATA_PATH", metadata_path)
    monkeypatch.setattr(model_loader, "MODEL_CLASS_MAP_PATH", class_map_path)
    monkeypatch.setattr(model_loader, "MODEL_CHECKPOINT_PATH", checkpoint_path)
    model_loader.load_category_model_artifacts.cache_clear()

    artifacts = model_loader.load_category_model_artifacts()

    assert artifacts.version == "test-v1"
    assert artifacts.class_names == ("fruit", "bread_or_bakery", "biryani")


def test_model_loader_raises_on_class_count_mismatch(tmp_path, monkeypatch) -> None:
    metadata_path = tmp_path / "metadata.json"
    class_map_path = tmp_path / "class_names.json"
    checkpoint_path = tmp_path / "checkpoint.mock"
    metadata_path.write_text(
        json.dumps(
            {
                "version": "test-v1",
                "trained_at": "2026-04-18T09:00:00Z",
                "output_dim": 2,
                "num_classes": 2,
                "class_map_file": "class_names.json",
                "checkpoint_file": "checkpoint.mock",
            }
        ),
        encoding="utf-8",
    )
    class_map_path.write_text(json.dumps({"class_names": ["fruit", "bread_or_bakery", "biryani"]}), encoding="utf-8")
    checkpoint_path.write_text("checkpoint", encoding="utf-8")

    monkeypatch.setattr(model_loader, "MODEL_METADATA_PATH", metadata_path)
    monkeypatch.setattr(model_loader, "MODEL_CLASS_MAP_PATH", class_map_path)
    monkeypatch.setattr(model_loader, "MODEL_CHECKPOINT_PATH", checkpoint_path)
    model_loader.load_category_model_artifacts.cache_clear()

    with pytest.raises(RuntimeError, match="Model output dimension mismatch"):
        model_loader.load_category_model_artifacts()


def test_model_loader_raises_on_duplicate_class_names(tmp_path, monkeypatch) -> None:
    metadata_path = tmp_path / "metadata.json"
    class_map_path = tmp_path / "class_names.json"
    checkpoint_path = tmp_path / "checkpoint.mock"
    metadata_path.write_text(
        json.dumps(
            {
                "version": "test-v1",
                "trained_at": "2026-04-18T09:00:00Z",
                "output_dim": 3,
                "num_classes": 3,
                "class_map_file": "class_names.json",
                "checkpoint_file": "checkpoint.mock",
            }
        ),
        encoding="utf-8",
    )
    class_map_path.write_text(json.dumps({"class_names": ["fruit", "fruit", "biryani"]}), encoding="utf-8")
    checkpoint_path.write_text("checkpoint", encoding="utf-8")

    monkeypatch.setattr(model_loader, "MODEL_METADATA_PATH", metadata_path)
    monkeypatch.setattr(model_loader, "MODEL_CLASS_MAP_PATH", class_map_path)
    monkeypatch.setattr(model_loader, "MODEL_CHECKPOINT_PATH", checkpoint_path)
    model_loader.load_category_model_artifacts.cache_clear()

    with pytest.raises(RuntimeError, match="duplicate class names"):
        model_loader.load_category_model_artifacts()


def test_model_loader_raises_on_missing_or_blank_class_name(tmp_path, monkeypatch) -> None:
    metadata_path = tmp_path / "metadata.json"
    class_map_path = tmp_path / "class_names.json"
    checkpoint_path = tmp_path / "checkpoint.mock"
    metadata_path.write_text(
        json.dumps(
            {
                "version": "test-v1",
                "trained_at": "2026-04-18T09:00:00Z",
                "output_dim": 3,
                "num_classes": 3,
                "class_map_file": "class_names.json",
                "checkpoint_file": "checkpoint.mock",
            }
        ),
        encoding="utf-8",
    )
    class_map_path.write_text(json.dumps({"class_names": ["fruit", "", "biryani"]}), encoding="utf-8")
    checkpoint_path.write_text("checkpoint", encoding="utf-8")

    monkeypatch.setattr(model_loader, "MODEL_METADATA_PATH", metadata_path)
    monkeypatch.setattr(model_loader, "MODEL_CLASS_MAP_PATH", class_map_path)
    monkeypatch.setattr(model_loader, "MODEL_CHECKPOINT_PATH", checkpoint_path)
    model_loader.load_category_model_artifacts.cache_clear()

    with pytest.raises(RuntimeError, match="missing or invalid class names"):
        model_loader.load_category_model_artifacts()


def test_model_loader_raises_when_metadata_points_to_stale_artifact_names(tmp_path, monkeypatch) -> None:
    metadata_path = tmp_path / "metadata.json"
    class_map_path = tmp_path / "class_names.json"
    checkpoint_path = tmp_path / "checkpoint.mock"
    metadata_path.write_text(
        json.dumps(
            {
                "version": "test-v1",
                "trained_at": "2026-04-18T09:00:00Z",
                "output_dim": 3,
                "num_classes": 3,
                "class_map_file": "wrong-class-map.json",
                "checkpoint_file": "wrong-checkpoint.mock",
            }
        ),
        encoding="utf-8",
    )
    class_map_path.write_text(json.dumps({"class_names": ["fruit", "bread_or_bakery", "biryani"]}), encoding="utf-8")
    checkpoint_path.write_text("checkpoint", encoding="utf-8")

    monkeypatch.setattr(model_loader, "MODEL_METADATA_PATH", metadata_path)
    monkeypatch.setattr(model_loader, "MODEL_CLASS_MAP_PATH", class_map_path)
    monkeypatch.setattr(model_loader, "MODEL_CHECKPOINT_PATH", checkpoint_path)
    model_loader.load_category_model_artifacts.cache_clear()

    with pytest.raises(RuntimeError, match="Metadata class_map_file mismatch"):
        model_loader.load_category_model_artifacts()
