#!/usr/bin/env python3
"""Generate reproducible case variants with different seeds and difficulty."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from generate_data import DEFAULT_SEED, GeneratorConfig, generate_dataset, write_dataset


PROFILES = [
    {"churn_logit_shift": -0.20, "seasonality_strength": 0.20, "missing_rate": 0.04},
    {"churn_logit_shift": 0.00, "seasonality_strength": 0.30, "missing_rate": 0.06},
    {"churn_logit_shift": 0.22, "seasonality_strength": 0.45, "missing_rate": 0.08},
]


def variant_config(
    variant_id: int,
    base_seed: int = DEFAULT_SEED,
    n_customers: int = 900,
    months: int = 8,
) -> GeneratorConfig:
    if variant_id < 1:
        raise ValueError("variant_id must be positive")
    profile = PROFILES[(variant_id - 1) % len(PROFILES)]
    return GeneratorConfig(
        seed=base_seed + 1009 * variant_id,
        n_customers=n_customers,
        months=months,
        missing_rate=profile["missing_rate"],
        duplicate_rate=0.01 + 0.002 * (variant_id % 3),
        outlier_rate=0.006 + 0.002 * (variant_id % 2),
        churn_logit_shift=profile["churn_logit_shift"],
        seasonality_strength=profile["seasonality_strength"],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent / "variants")
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--base-seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--n-customers", type=int, default=900)
    parser.add_argument("--months", type=int, default=8)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.count < 1:
        raise ValueError("count must be positive")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    variants: list[dict[str, object]] = []
    for variant_id in range(1, args.count + 1):
        config = variant_config(variant_id, args.base_seed, args.n_customers, args.months)
        output_path = args.output_dir / f"variant-{variant_id:02d}.csv"
        manifest = write_dataset(generate_dataset(config), config, output_path)
        variants.append(
            {
                "variant_id": variant_id,
                "file": output_path.name,
                "parameters": asdict(config),
                "sha256": manifest["sha256"],
                "positive_rate": manifest["positive_rate"],
            }
        )
    (args.output_dir / "variants.json").write_text(
        json.dumps(variants, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(variants, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
