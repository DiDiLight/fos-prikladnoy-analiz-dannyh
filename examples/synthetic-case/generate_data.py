#!/usr/bin/env python3
"""Generate a reproducible synthetic subscriber-retention dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd


GENERATOR_VERSION = "1.0.0"
DEFAULT_SEED = 20260728

SCHEMA = {
    "row_id": {"type": "string", "role": "identifier", "available_at_decision": True},
    "customer_id": {"type": "string", "role": "group", "available_at_decision": True},
    "snapshot_date": {"type": "date", "role": "time", "available_at_decision": True},
    "region": {"type": "category", "role": "feature", "available_at_decision": True},
    "plan_type": {"type": "category", "role": "feature", "available_at_decision": True},
    "acquisition_channel": {"type": "category", "role": "feature", "available_at_decision": True},
    "autopay": {"type": "category", "role": "feature", "available_at_decision": True},
    "tenure_months": {"type": "integer", "role": "feature", "available_at_decision": True},
    "monthly_fee": {"type": "number", "role": "feature", "available_at_decision": True},
    "usage_hours_30d": {"type": "number", "role": "feature", "available_at_decision": True},
    "usage_change_90d": {"type": "number", "role": "feature", "available_at_decision": True},
    "support_tickets_90d": {"type": "integer", "role": "feature", "available_at_decision": True},
    "late_payments_6m": {"type": "integer", "role": "feature", "available_at_decision": True},
    "satisfaction_score": {"type": "number", "role": "feature", "available_at_decision": True},
    "days_since_last_login": {"type": "number", "role": "feature", "available_at_decision": True},
    "network_incidents_30d": {"type": "integer", "role": "feature", "available_at_decision": True},
    "leaked_churn_score": {
        "type": "number",
        "role": "intentional_leakage",
        "available_at_decision": False,
    },
    "retention_offer_result_14d": {
        "type": "category",
        "role": "post_decision_feature",
        "available_at_decision": False,
    },
    "churn_30d": {"type": "integer", "role": "target", "available_at_decision": False},
}


@dataclass(frozen=True)
class GeneratorConfig:
    seed: int = DEFAULT_SEED
    n_customers: int = 1200
    months: int = 8
    start_date: str = "2024-01-01"
    missing_rate: float = 0.06
    duplicate_rate: float = 0.015
    outlier_rate: float = 0.008
    churn_logit_shift: float = 0.0
    seasonality_strength: float = 0.30


def _sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-values))


def _validate_config(config: GeneratorConfig) -> None:
    if config.n_customers < 100:
        raise ValueError("n_customers must be at least 100")
    if config.months < 4:
        raise ValueError("months must be at least 4")
    for name in ("missing_rate", "duplicate_rate", "outlier_rate"):
        value = getattr(config, name)
        if not 0 <= value < 0.25:
            raise ValueError(f"{name} must be in [0, 0.25)")


def generate_dataset(config: GeneratorConfig) -> pd.DataFrame:
    """Return a deterministic dataset with intentional quality problems."""

    _validate_config(config)
    rng = np.random.default_rng(config.seed)
    n = config.n_customers

    customer_id = np.array([f"C{index:05d}" for index in range(1, n + 1)])
    region = rng.choice(["north", "south", "east", "west"], n, p=[0.26, 0.24, 0.28, 0.22])
    plan_type = rng.choice(["basic", "standard", "premium"], n, p=[0.45, 0.40, 0.15])
    acquisition = rng.choice(["organic", "partner", "advertising", "referral"], n, p=[0.35, 0.20, 0.30, 0.15])
    autopay = rng.choice(["yes", "no"], n, p=[0.68, 0.32])
    initial_tenure = rng.integers(1, 49, size=n)
    customer_effect = rng.normal(0, 0.45, size=n)
    base_usage = rng.gamma(shape=4.2, scale=7.5, size=n)
    base_satisfaction = np.clip(rng.normal(3.7, 0.65, size=n), 1, 5)

    plan_fee = {"basic": 29.0, "standard": 49.0, "premium": 79.0}
    plan_risk = {"basic": 0.18, "standard": 0.0, "premium": -0.12}
    region_risk = {"north": -0.05, "south": 0.18, "east": 0.0, "west": 0.08}

    frames: list[pd.DataFrame] = []
    dates = pd.date_range(config.start_date, periods=config.months, freq="MS")
    row_counter = 0

    for month_index, snapshot_date in enumerate(dates):
        seasonal = config.seasonality_strength * np.sin(2 * np.pi * month_index / 12)
        incidents = rng.poisson(
            np.clip(0.45 + 0.15 * (region == "south") + 0.06 * month_index, 0.05, None)
        )
        support_tickets = rng.poisson(0.35 + 0.55 * incidents)
        late_payments = rng.binomial(3, np.where(autopay == "yes", 0.035, 0.12))
        usage_change = np.clip(
            rng.normal(-0.015 * month_index, 0.18, n)
            - 0.06 * support_tickets
            - 0.04 * late_payments,
            -0.85,
            0.75,
        )
        usage = np.clip(base_usage * (1 + usage_change) + rng.normal(0, 2.5, n), 0, None)
        satisfaction = np.clip(
            base_satisfaction - 0.20 * incidents - 0.13 * support_tickets + rng.normal(0, 0.25, n),
            1,
            5,
        )
        days_since_login = np.clip(
            rng.gamma(2.2, 3.2, n) + 5.0 * (usage_change < -0.25) + 2.5 * late_payments,
            0,
            None,
        )
        fee = np.array([plan_fee[value] for value in plan_type]) + rng.normal(0, 2.0, n)

        logit = (
            -2.75
            + config.churn_logit_shift
            + seasonal
            + customer_effect
            + 0.32 * support_tickets
            + 0.38 * late_payments
            + 0.035 * days_since_login
            - 0.48 * (satisfaction - 3.0)
            - 0.75 * (autopay == "yes")
            - 1.25 * usage_change
            + np.array([plan_risk[value] for value in plan_type])
            + np.array([region_risk[value] for value in region])
            + 0.045 * month_index
        )
        churn_probability = _sigmoid(logit)
        target = rng.binomial(1, churn_probability)

        leaked_score = np.clip(0.08 + 0.82 * target + rng.normal(0, 0.06, n), 0, 1)
        offer_result = np.where(
            target == 1,
            rng.choice(["cancelled", "retained_after_offer"], n, p=[0.78, 0.22]),
            rng.choice(["no_contact", "accepted_offer"], n, p=[0.82, 0.18]),
        )

        row_ids = [f"S{config.seed}-{index:07d}" for index in range(row_counter, row_counter + n)]
        row_counter += n
        frames.append(
            pd.DataFrame(
                {
                    "row_id": row_ids,
                    "customer_id": customer_id,
                    "snapshot_date": snapshot_date.strftime("%Y-%m-%d"),
                    "region": region,
                    "plan_type": plan_type,
                    "acquisition_channel": acquisition,
                    "autopay": autopay,
                    "tenure_months": initial_tenure + month_index,
                    "monthly_fee": fee.round(2),
                    "usage_hours_30d": usage.round(3),
                    "usage_change_90d": usage_change.round(4),
                    "support_tickets_90d": support_tickets,
                    "late_payments_6m": late_payments,
                    "satisfaction_score": satisfaction.round(2),
                    "days_since_last_login": days_since_login.round(2),
                    "network_incidents_30d": incidents,
                    "leaked_churn_score": leaked_score.round(4),
                    "retention_offer_result_14d": offer_result,
                    "churn_30d": target,
                }
            )
        )

    data = pd.concat(frames, ignore_index=True)

    missing_columns = [
        "acquisition_channel",
        "usage_hours_30d",
        "usage_change_90d",
        "satisfaction_score",
    ]
    missing_count = max(1, int(round(len(data) * config.missing_rate)))
    for column in missing_columns:
        indices = rng.choice(data.index.to_numpy(), size=missing_count, replace=False)
        data.loc[indices, column] = np.nan

    outlier_count = max(1, int(round(len(data) * config.outlier_rate)))
    usage_outliers = rng.choice(data.index.to_numpy(), size=outlier_count, replace=False)
    fee_outliers = rng.choice(data.index.to_numpy(), size=outlier_count, replace=False)
    data.loc[usage_outliers, "usage_hours_30d"] = (
        data.loc[usage_outliers, "usage_hours_30d"].fillna(40) * rng.uniform(8, 14, outlier_count)
    ).round(3)
    data.loc[fee_outliers, "monthly_fee"] = (
        data.loc[fee_outliers, "monthly_fee"] * rng.uniform(7, 12, outlier_count)
    ).round(2)

    duplicate_count = max(1, int(round(len(data) * config.duplicate_rate)))
    duplicate_indices = rng.choice(data.index.to_numpy(), size=duplicate_count, replace=False)
    data = pd.concat([data, data.loc[duplicate_indices]], ignore_index=True)
    data = data.iloc[rng.permutation(len(data))].reset_index(drop=True)
    return data[list(SCHEMA)]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_dataset(data: pd.DataFrame, config: GeneratorConfig, output_path: Path) -> dict[str, object]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(output_path, index=False, lineterminator="\n", float_format="%.6f")

    manifest = {
        "generator_version": GENERATOR_VERSION,
        "parameters": asdict(config),
        "rows_with_duplicates": int(len(data)),
        "unique_rows": int(len(data.drop_duplicates())),
        "positive_rate": round(float(data["churn_30d"].mean()), 6),
        "sha256": sha256_file(output_path),
    }
    manifest_path = output_path.with_name("generation-manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    schema_path = output_path.with_name("schema.json")
    schema_path.write_text(json.dumps(SCHEMA, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "data" / "subscriber_retention.csv")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--n-customers", type=int, default=1200)
    parser.add_argument("--months", type=int, default=8)
    parser.add_argument("--start-date", default="2024-01-01")
    parser.add_argument("--missing-rate", type=float, default=0.06)
    parser.add_argument("--duplicate-rate", type=float, default=0.015)
    parser.add_argument("--outlier-rate", type=float, default=0.008)
    parser.add_argument("--churn-logit-shift", type=float, default=0.0)
    parser.add_argument("--seasonality-strength", type=float, default=0.30)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = GeneratorConfig(
        seed=args.seed,
        n_customers=args.n_customers,
        months=args.months,
        start_date=args.start_date,
        missing_rate=args.missing_rate,
        duplicate_rate=args.duplicate_rate,
        outlier_rate=args.outlier_rate,
        churn_logit_shift=args.churn_logit_shift,
        seasonality_strength=args.seasonality_strength,
    )
    data = generate_dataset(config)
    manifest = write_dataset(data, config, args.output)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
