# Category-Aware Freshness Training Scaffold

This folder is a placeholder training scaffold for future image-based freshness models.

## Expected Dataset Layout

```text
dataset/
  fruit/
    fresh/
    about_to_spoil/
    spoiled/
  biryani/
    fresh/
    about_to_spoil/
    spoiled/
  roti/
    fresh/
    dry_or_stale/
    spoiled/
  curry/
    fresh/
    oil_separated_or_stale/
    spoiled/
  rice/
    fresh/
    about_to_spoil/
    spoiled/
  kebab/
    fresh/
    about_to_spoil/
    spoiled/
  dessert/
    fresh/
    about_to_spoil/
    spoiled/
  fried_rice/
    fresh/
    about_to_spoil/
    spoiled/
  haleem/
    fresh/
    about_to_spoil/
    spoiled/
  bread_or_bakery/
    fresh/
    dry_or_stale/
    spoiled/
```

## Manifest Schema

The manifest should capture:

- `image_path`
- `food_category`
- `freshness_label`
- `food_type`
- `prepared_time`
- `storage_condition`
- `split`

Use `build_dataset_manifest.py` to scan the dataset tree and emit a CSV manifest.

## Training Goals

- category-aware training
- class-balanced sampling
- per-class precision / recall / F1
- confusion matrix export
- especially high recall focus on `spoiled` classes

The scaffold in `train_category_freshness.py` expects optional ML dependencies and is intentionally isolated from runtime app code.

## Required Saved Artifacts

Every trained category classifier should save:

- `checkpoint.pt` or `checkpoint.onnx`
- `class_names.json`
- `metadata.json`

`metadata.json` should include at least:

- `version`
- `trained_at`
- `output_dim`
- `num_classes`
- `backbone`
- `class_map_file`
- `checkpoint_file`
