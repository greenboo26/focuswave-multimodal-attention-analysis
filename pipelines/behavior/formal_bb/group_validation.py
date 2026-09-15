"""Participant-group-safe cross-validation helpers.

Feature imputation, scaling, and univariate selection are deliberately fitted
inside a single training fold.  Callers receive no globally fitted object.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.impute import SimpleImputer
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


GROUP_COLUMN = "anonymous_participant_group_id"


def assert_group_disjoint(
    train: pd.DataFrame,
    test: pd.DataFrame,
    group_column: str = GROUP_COLUMN,
) -> None:
    """Raise if any anonymous participant group crosses a fold boundary."""
    overlap = set(train[group_column].dropna()) & set(test[group_column].dropna())
    if overlap:
        raise ValueError(f"participant-group leakage: {sorted(overlap)}")


def build_group_kfold_assignments(
    frame: pd.DataFrame,
    n_splits: int,
    *,
    session_column: str = "session_id",
    group_column: str = GROUP_COLUMN,
) -> pd.DataFrame:
    """Return one fold per session while keeping every group in one fold."""
    required = {session_column, group_column}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"missing grouping columns: {sorted(missing)}")
    mapping = frame[[session_column, group_column]].drop_duplicates()
    per_session = mapping.groupby(session_column)[group_column].nunique(dropna=False)
    if (per_session != 1).any() or mapping[group_column].isna().any():
        raise ValueError("each session must map to exactly one non-null participant group")
    groups = mapping[group_column].nunique()
    if not 2 <= n_splits <= groups:
        raise ValueError(f"n_splits={n_splits} requires at least that many groups; found {groups}")
    splitter = GroupKFold(n_splits=n_splits)
    mapping = mapping.reset_index(drop=True)
    mapping["fold_id"] = -1
    for fold_id, (_, test_index) in enumerate(
        splitter.split(mapping, groups=mapping[group_column])
    ):
        mapping.loc[test_index, "fold_id"] = fold_id
    if (mapping["fold_id"] < 0).any():
        raise RuntimeError("incomplete fold assignment")
    for fold_id in range(n_splits):
        test = mapping[mapping.fold_id == fold_id]
        train = mapping[mapping.fold_id != fold_id]
        assert_group_disjoint(train, test, group_column)
    return mapping.sort_values(["fold_id", session_column]).reset_index(drop=True)


@dataclass(frozen=True)
class FoldTransformResult:
    train: np.ndarray
    test: np.ndarray
    selected_features: tuple[str, ...]
    scaler_mean: tuple[float, ...]
    pipeline: Pipeline


def fit_transform_train_only(
    train: pd.DataFrame,
    test: pd.DataFrame,
    *,
    feature_columns: list[str],
    target_column: str,
    select_k: int | str = "all",
    group_column: str = GROUP_COLUMN,
) -> FoldTransformResult:
    """Fit imputation, scaling, and feature selection on the training fold only."""
    assert_group_disjoint(train, test, group_column)
    if not feature_columns:
        raise ValueError("feature_columns must not be empty")
    if select_k != "all" and not 1 <= int(select_k) <= len(feature_columns):
        raise ValueError("select_k must be 'all' or between 1 and feature count")
    y_train = train[target_column]
    if y_train.isna().any() or y_train.nunique() < 2:
        raise ValueError("training target must contain at least two non-null classes")
    pipe = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("selector", SelectKBest(score_func=f_classif, k=select_k)),
        ]
    )
    train_x = pipe.fit_transform(train[feature_columns], y_train)
    test_x = pipe.transform(test[feature_columns])
    support = pipe.named_steps["selector"].get_support()
    selected = tuple(np.asarray(feature_columns)[support].tolist())
    means = tuple(float(x) for x in pipe.named_steps["scaler"].mean_)
    return FoldTransformResult(train_x, test_x, selected, means, pipe)
