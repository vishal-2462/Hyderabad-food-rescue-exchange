from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATASET_ROOT = ROOT / "dataset"
OUTPUT_PATH = ROOT / "sample_dataset_manifest.csv"


def build_manifest() -> None:
    rows: list[dict[str, str]] = []
    for category_dir in sorted(path for path in DATASET_ROOT.iterdir() if path.is_dir()):
        for label_dir in sorted(path for path in category_dir.iterdir() if path.is_dir()):
            for image_path in sorted(label_dir.rglob("*")):
                if not image_path.is_file():
                    continue
                if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
                    continue
                rows.append(
                    {
                        "image_path": str(image_path.relative_to(ROOT)),
                        "food_category": category_dir.name,
                        "freshness_label": label_dir.name,
                        "food_type": category_dir.name,
                        "prepared_time": "",
                        "storage_condition": "",
                        "split": "train",
                    }
                )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["image_path", "food_category", "freshness_label", "food_type", "prepared_time", "storage_condition", "split"],
        )
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    if not DATASET_ROOT.exists():
        raise SystemExit(f"Dataset root not found: {DATASET_ROOT}")
    build_manifest()
    print(f"Wrote manifest to {OUTPUT_PATH}")
