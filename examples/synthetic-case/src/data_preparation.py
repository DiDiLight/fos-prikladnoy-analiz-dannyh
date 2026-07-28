"""Schema checks, safe features, and temporal splitting for the case."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


TARGET_COLUMN = "churn_30d"
IDENTIFIER_COLUMNS = ["row_id", "customer_id", "snapshot_date"]
FORBIDDEN_FEATURES = ["leaked_churn_score", "retention_offer_result_14d"]

NUMERIC_FEATURES = [
    "tenure_months",
    "monthly_fee",
    "usage_hours_30d",
    "usage_change_90d",
    "support_tickets_90d",
    "late_payments_6m",
    "satisfaction_score",
    "days_since_last_login",
    "network_incidents_30d",
]

CATEGORICAL_FEATURES = [
    "region",
    "plan_type",
    "acquisition_channel",
    "autopay",
]

SAFE_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
REQUIRED_COLUMNS = IDENTIFIER_COLUMNS + SAFE_FEATURES + FORBIDDEN_FEATURES + [TARGET_COLUMN]
GROUP_SPLIT_SEED = 20260728


def load_data(path: str | Path) -> pd.DataFrame:
    data = pd.read_csv(path, parse_dates=["snapshot_date"])
    validate_schema(data)
    return data


def validate_schema(data: pd.DataFrame) -> None:
    missing = sorted(set(REQUIRED_COLUMNS) - set(data.columns))
    if missing:
        raise ValueError(f"missing required columns: {missing}")
    if not data["row_id"].notna().all() or not data["customer_id"].notna().all():
        raise ValueError("identifiers must not be missing")
    if data["snapshot_date"].isna().any():
        raise ValueError("snapshot_date contains invalid values")
    target_values = set(data[TARGET_COLUMN].dropna().unique())
    if not target_values <= {0, 1}:
        raise ValueError(f"{TARGET_COLUMN} must be binary, got {target_values}")
    if set(SAFE_FEATURES) & set(FORBIDDEN_FEATURES):
        raise ValueError("safe feature list contains forbidden fields")


def remove_exact_duplicates(data: pd.DataFrame) -> pd.DataFrame:
    return data.drop_duplicates().reset_index(drop=True)


def temporal_split(data: pd.DataFrame, test_months: int = 2) -> tuple[pd.DataFrame, pd.DataFrame, pd.Timestamp]:
    unique_dates = pd.Series(data["snapshot_date"].dropna().unique()).sort_values().tolist()
    if len(unique_dates) <= test_months:
        raise ValueError("not enough unique dates for temporal split")
    cutoff = pd.Timestamp(unique_dates[-test_months])
    train = data.loc[data["snapshot_date"] < cutoff].copy()
    test = data.loc[data["snapshot_date"] >= cutoff].copy()
    if train.empty or test.empty:
        raise ValueError("temporal split produced an empty partition")
    if train["snapshot_date"].max() >= test["snapshot_date"].min():
        raise ValueError("temporal split overlaps")
    return train, test, cutoff


def group_split(
    data: pd.DataFrame,
    test_size: float = 0.20,
    random_state: int = GROUP_SPLIT_SEED,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
    train_indices, test_indices = next(splitter.split(data, groups=data["customer_id"]))
    train = data.iloc[train_indices].copy()
    test = data.iloc[test_indices].copy()
    if set(train["customer_id"]) & set(test["customer_id"]):
        raise ValueError("group split contains customers in both partitions")
    return train, test


def features_and_target(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    return data[SAFE_FEATURES].copy(), data[TARGET_COLUMN].astype(int).copy()


def build_preprocessor() -> ColumnTransformer:
    numeric_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    return ColumnTransformer(
        [
            ("numeric", numeric_pipeline, NUMERIC_FEATURES),
            ("categorical", categorical_pipeline, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )
