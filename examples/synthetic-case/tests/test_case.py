from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal
from sklearn.metrics import roc_auc_score


CASE_ROOT = Path(__file__).resolve().parents[1]
if str(CASE_ROOT) not in sys.path:
    sys.path.insert(0, str(CASE_ROOT))

from generate_data import DEFAULT_SEED, SCHEMA, GeneratorConfig, generate_dataset, write_dataset
from generate_variants import variant_config
from src.data_preparation import (
    CATEGORICAL_FEATURES,
    FORBIDDEN_FEATURES,
    NUMERIC_FEATURES,
    SAFE_FEATURES,
    build_preprocessor,
    features_and_target,
    group_split,
    load_data,
    remove_exact_duplicates,
    temporal_split,
)
from teacher.baseline import check_expected_ranges, load_expected_ranges, run_baseline


class GenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.small_config = GeneratorConfig(seed=12345, n_customers=240, months=6)
        cls.data = generate_dataset(cls.small_config)

    def test_fixed_seed_is_reproducible(self) -> None:
        first = generate_dataset(self.small_config)
        second = generate_dataset(self.small_config)
        assert_frame_equal(first, second, check_exact=True)

    def test_different_seed_changes_data(self) -> None:
        other = generate_dataset(GeneratorConfig(seed=12346, n_customers=240, months=6))
        self.assertFalse(self.data.equals(other))

    def test_schema_and_types(self) -> None:
        self.assertEqual(list(self.data.columns), list(SCHEMA))
        self.assertTrue(set(self.data["churn_30d"].unique()) <= {0, 1})
        pd.to_datetime(self.data["snapshot_date"], errors="raise")
        self.assertTrue(set(NUMERIC_FEATURES) <= set(self.data.columns))
        self.assertTrue(set(CATEGORICAL_FEATURES) <= set(self.data.columns))

    def test_intentional_quality_problems_exist(self) -> None:
        self.assertGreater(int(self.data.duplicated().sum()), 0)
        self.assertGreater(int(self.data[["usage_hours_30d", "satisfaction_score"]].isna().sum().sum()), 0)
        self.assertGreater(int((self.data["monthly_fee"] > 300).sum()), 0)
        positive_rate = float(self.data["churn_30d"].mean())
        self.assertGreater(positive_rate, 0.05)
        self.assertLess(positive_rate, 0.35)

    def test_leakage_and_post_decision_fields_are_declared(self) -> None:
        self.assertEqual(set(FORBIDDEN_FEATURES), {"leaked_churn_score", "retention_offer_result_14d"})
        for field in FORBIDDEN_FEATURES:
            self.assertFalse(SCHEMA[field]["available_at_decision"])
            self.assertNotIn(field, SAFE_FEATURES)
        self.assertNotIn("churn_30d", SAFE_FEATURES)
        self.assertGreater(
            roc_auc_score(self.data["churn_30d"], self.data["leaked_churn_score"]),
            0.98,
        )

    def test_variant_generator_changes_seed_and_parameters(self) -> None:
        first = variant_config(1, n_customers=200, months=6)
        second = variant_config(2, n_customers=200, months=6)
        self.assertNotEqual(first.seed, second.seed)
        self.assertNotEqual(first.missing_rate, second.missing_rate)
        self.assertNotEqual(first.churn_logit_shift, second.churn_logit_shift)


class PreparationAndBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.data_path = Path(cls.temp_dir.name) / "case.csv"
        config = GeneratorConfig(seed=DEFAULT_SEED, n_customers=500, months=8)
        write_dataset(generate_dataset(config), config, cls.data_path)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_dir.cleanup()

    def test_temporal_split_does_not_overlap(self) -> None:
        data = remove_exact_duplicates(load_data(self.data_path))
        train, test, _ = temporal_split(data)
        self.assertLess(train["snapshot_date"].max(), test["snapshot_date"].min())

    def test_group_split_does_not_share_customers(self) -> None:
        data = remove_exact_duplicates(load_data(self.data_path))
        train, test = group_split(data)
        self.assertFalse(set(train["customer_id"]) & set(test["customer_id"]))

    def test_preprocessor_uses_only_safe_fields(self) -> None:
        transformer = build_preprocessor()
        configured = []
        for _, _, columns in transformer.transformers:
            configured.extend(columns)
        self.assertEqual(set(configured), set(SAFE_FEATURES))
        self.assertFalse(set(configured) & set(FORBIDDEN_FEATURES))

    def test_feature_extraction_excludes_leakage(self) -> None:
        data = load_data(self.data_path)
        features, target = features_and_target(data)
        self.assertEqual(list(features.columns), SAFE_FEATURES)
        self.assertEqual(len(features), len(target))

    def test_baseline_is_reproducible(self) -> None:
        first = run_baseline(self.data_path)
        second = run_baseline(self.data_path)
        self.assertEqual(first, second)

    def test_committed_default_baseline_is_in_expected_range(self) -> None:
        default_path = CASE_ROOT / "data" / "subscriber_retention.csv"
        if not default_path.exists():
            self.skipTest("default generated data has not been created")
        metrics = run_baseline(default_path)
        self.assertEqual(check_expected_ranges(metrics, load_expected_ranges()), [])

    def test_generation_manifest_matches_default_file(self) -> None:
        manifest_path = CASE_ROOT / "data" / "generation-manifest.json"
        if not manifest_path.exists():
            self.skipTest("default generation manifest has not been created")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["parameters"]["seed"], DEFAULT_SEED)
        self.assertEqual(manifest["generator_version"], "1.0.0")

    def test_default_dataset_rebuilds_byte_for_byte(self) -> None:
        default_path = CASE_ROOT / "data" / "subscriber_retention.csv"
        committed_manifest = json.loads(
            (CASE_ROOT / "data" / "generation-manifest.json").read_text(encoding="utf-8")
        )
        rebuilt_path = Path(self.temp_dir.name) / "rebuilt-default.csv"
        rebuilt_manifest = write_dataset(
            generate_dataset(GeneratorConfig()),
            GeneratorConfig(),
            rebuilt_path,
        )
        self.assertEqual(rebuilt_manifest["sha256"], committed_manifest["sha256"])
        self.assertEqual(rebuilt_path.read_bytes(), default_path.read_bytes())


if __name__ == "__main__":
    unittest.main()
