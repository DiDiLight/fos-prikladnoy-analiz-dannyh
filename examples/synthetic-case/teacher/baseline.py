#!/usr/bin/env python3
"""Reference leakage-safe baseline for the synthetic retention case."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, f1_score, roc_auc_score
from sklearn.pipeline import Pipeline


CASE_ROOT = Path(__file__).resolve().parents[1]
if str(CASE_ROOT) not in sys.path:
    sys.path.insert(0, str(CASE_ROOT))

from src.data_preparation import (  # noqa: E402
    FORBIDDEN_FEATURES,
    SAFE_FEATURES,
    build_preprocessor,
    features_and_target,
    load_data,
    remove_exact_duplicates,
    temporal_split,
)


MODEL_SEED = 20260728
DECISION_SHARE = 0.15
DECISION_THRESHOLD = 0.50


def _top_share_metrics(y_true: np.ndarray, probabilities: np.ndarray, share: float) -> tuple[float, float]:
    count = max(1, int(np.ceil(len(probabilities) * share)))
    selected = np.argsort(-probabilities)[:count]
    true_positives = int(y_true[selected].sum())
    precision = true_positives / count
    recall = true_positives / max(1, int(y_true.sum()))
    return precision, recall


def run_baseline(data_path: str | Path, model_seed: int = MODEL_SEED) -> dict[str, object]:
    data = remove_exact_duplicates(load_data(data_path))
    train, test, cutoff = temporal_split(data, test_months=2)
    x_train, y_train = features_and_target(train)
    x_test, y_test = features_and_target(test)

    pipeline = Pipeline(
        [
            ("preprocess", build_preprocessor()),
            (
                "model",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=model_seed,
                    solver="lbfgs",
                ),
            ),
        ]
    )
    pipeline.fit(x_train, y_train)
    probabilities = pipeline.predict_proba(x_test)[:, 1]
    predictions = (probabilities >= DECISION_THRESHOLD).astype(int)
    precision_top, recall_top = _top_share_metrics(y_test.to_numpy(), probabilities, DECISION_SHARE)

    return {
        "run_id": f"safe-logreg-seed-{model_seed}",
        "model_seed": model_seed,
        "cutoff_date": cutoff.strftime("%Y-%m-%d"),
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "train_positive_rate": round(float(y_train.mean()), 6),
        "test_positive_rate": round(float(y_test.mean()), 6),
        "roc_auc": round(float(roc_auc_score(y_test, probabilities)), 6),
        "average_precision": round(float(average_precision_score(y_test, probabilities)), 6),
        "f1_at_0_50": round(float(f1_score(y_test, predictions)), 6),
        "precision_at_top_15pct": round(float(precision_top), 6),
        "recall_at_top_15pct": round(float(recall_top), 6),
        "safe_feature_count": len(SAFE_FEATURES),
        "excluded_fields": FORBIDDEN_FEATURES,
    }


def load_expected_ranges(path: Path | None = None) -> dict[str, list[float]]:
    range_path = path or CASE_ROOT / "teacher" / "expected_metric_ranges.json"
    payload = json.loads(range_path.read_text(encoding="utf-8"))
    return payload["ranges"]


def check_expected_ranges(metrics: dict[str, object], ranges: dict[str, list[float]]) -> list[str]:
    errors: list[str] = []
    for name, limits in ranges.items():
        value = float(metrics[name])
        lower, upper = limits
        if not lower <= value <= upper:
            errors.append(f"{name}={value:.6f} outside [{lower}, {upper}]")
    return errors


def write_outputs(metrics: dict[str, object], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "baseline-metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    fields = [
        "run_id",
        "model_seed",
        "cutoff_date",
        "train_rows",
        "test_rows",
        "roc_auc",
        "average_precision",
        "f1_at_0_50",
        "precision_at_top_15pct",
        "recall_at_top_15pct",
    ]
    with (output_dir / "experiment-log.csv").open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerow({field: metrics[field] for field in fields})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data",
        type=Path,
        default=CASE_ROOT / "data" / "subscriber_retention.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=CASE_ROOT / "teacher" / "reference-output",
    )
    parser.add_argument("--model-seed", type=int, default=MODEL_SEED)
    parser.add_argument("--check-range", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metrics = run_baseline(args.data, args.model_seed)
    write_outputs(metrics, args.output_dir)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    if args.check_range:
        errors = check_expected_ranges(metrics, load_expected_ranges())
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
