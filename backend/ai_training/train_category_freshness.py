from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path


try:
    import pandas as pd  # type: ignore
except ImportError:  # pragma: no cover - optional training dependency
    pd = None


@dataclass(slots=True)
class TrainingConfig:
    manifest_path: Path
    target_category: str | None
    backbone: str
    class_balanced: bool
    output_dir: Path


def load_manifest(manifest_path: Path):
    if pd is None:
        raise RuntimeError("Optional training dependency 'pandas' is not installed. Install pandas, torch, torchvision, and scikit-learn to run training.")
    return pd.read_csv(manifest_path)


def summarize_manifest(frame, target_category: str | None) -> None:
    working = frame if target_category is None else frame[frame["food_category"] == target_category]
    if working.empty:
        raise RuntimeError(f"No rows found for category {target_category!r}")

    print("Training rows:", len(working))
    print("Categories:")
    for category, count in sorted(Counter(working["food_category"]).items()):
        print(f"  - {category}: {count}")
    print("Labels:")
    for label, count in sorted(Counter(working["freshness_label"]).items()):
        print(f"  - {label}: {count}")


def compute_class_weights(frame) -> dict[str, float]:
    counts = Counter(frame["freshness_label"])
    total = sum(counts.values())
    return {label: round(total / max(count * len(counts), 1), 4) for label, count in counts.items()}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Category-aware freshness training scaffold")
    parser.add_argument("--manifest", default=str(Path(__file__).resolve().parent / "sample_dataset_manifest.csv"))
    parser.add_argument("--category", default=None)
    parser.add_argument("--backbone", default="mobilenet_v2", choices=["mobilenet_v2", "efficientnet_b0"])
    parser.add_argument("--no-class-balance", action="store_true")
    parser.add_argument("--output-dir", default=str(Path(__file__).resolve().parent / "artifacts" / "freshness-category-v2"))
    return parser


def save_inference_artifacts(frame, output_dir: Path, backbone: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    class_names = sorted(set(frame["food_category"]))
    (output_dir / "class_names.json").write_text(json.dumps({"class_names": class_names}, indent=2), encoding="utf-8")
    metadata = {
        "version": output_dir.name,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "output_dim": len(class_names),
        "num_classes": len(class_names),
        "backbone": backbone,
        "class_map_file": "class_names.json",
        "checkpoint_file": "checkpoint.mock",
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (output_dir / "checkpoint.mock").write_text("replace-with-real-trained-model", encoding="utf-8")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config = TrainingConfig(
        manifest_path=Path(args.manifest),
        target_category=args.category,
        backbone=args.backbone,
        class_balanced=not args.no_class_balance,
        output_dir=Path(args.output_dir),
    )

    frame = load_manifest(config.manifest_path)
    summarize_manifest(frame, config.target_category)
    if config.class_balanced:
        print("Class weights:", compute_class_weights(frame if config.target_category is None else frame[frame["food_category"] == config.target_category]))

    save_inference_artifacts(frame if config.target_category is None else frame[frame["food_category"] == config.target_category], config.output_dir, config.backbone)
    print(f"Saved inference artifacts to {config.output_dir}")

    print("\nScaffold only:")
    print("- plug in torchvision dataset loading here")
    print("- train a 3-class minimum classifier per category")
    print("- export confusion matrix and per-class precision/recall/F1")
    print("- optimize especially for spoiled-class recall")


if __name__ == "__main__":
    main()
