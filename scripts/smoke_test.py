#!/usr/bin/env python3
"""Run a fast end-to-end check of the synthetic teaching case."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASE_ROOT = ROOT / "examples" / "synthetic-case"
if str(CASE_ROOT) not in sys.path:
    sys.path.insert(0, str(CASE_ROOT))

from generate_data import GeneratorConfig, generate_dataset, write_dataset  # noqa: E402
from src.data_preparation import (  # noqa: E402
    FORBIDDEN_FEATURES,
    SAFE_FEATURES,
    features_and_target,
    load_data,
    remove_exact_duplicates,
)
from teacher.baseline import run_baseline  # noqa: E402


SMOKE_SEED = 20260729


def main() -> int:
    config = GeneratorConfig(seed=SMOKE_SEED, n_customers=240, months=6)
    with tempfile.TemporaryDirectory(prefix="fos-smoke-") as temporary_directory:
        data_path = Path(temporary_directory) / "subscriber_retention_smoke.csv"
        generated = generate_dataset(config)
        manifest = write_dataset(generated, config, data_path)

        actual_digest = hashlib.sha256(data_path.read_bytes()).hexdigest()
        if actual_digest != manifest["sha256"]:
            raise RuntimeError("generated CSV checksum differs from its manifest")

        data = remove_exact_duplicates(load_data(data_path))
        features, target = features_and_target(data)
        if list(features.columns) != SAFE_FEATURES:
            raise RuntimeError("reference feature set differs from SAFE_FEATURES")
        if set(features.columns) & set(FORBIDDEN_FEATURES):
            raise RuntimeError("forbidden fields reached the reference feature matrix")
        if target.nunique() != 2:
            raise RuntimeError("smoke dataset does not contain both target classes")

        metrics = run_baseline(data_path)
        if set(metrics["excluded_fields"]) != set(FORBIDDEN_FEATURES):
            raise RuntimeError("baseline does not report all forbidden fields as excluded")
        for metric_name in (
            "roc_auc",
            "average_precision",
            "f1_at_0_50",
            "precision_at_top_15pct",
            "recall_at_top_15pct",
        ):
            value = float(metrics[metric_name])
            if not 0.0 <= value <= 1.0:
                raise RuntimeError(f"{metric_name} is outside [0, 1]: {value}")

        summary = {
            "status": "ok",
            "seed": SMOKE_SEED,
            "rows_with_duplicates": manifest["rows_with_duplicates"],
            "train_rows": metrics["train_rows"],
            "test_rows": metrics["test_rows"],
            "roc_auc": metrics["roc_auc"],
            "excluded_fields": metrics["excluded_fields"],
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
