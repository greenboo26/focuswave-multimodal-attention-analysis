"""Reusable formal BB behavior production and participant-safe validation."""

from .group_validation import (
    assert_group_disjoint,
    build_group_kfold_assignments,
    fit_transform_train_only,
)

__all__ = [
    "assert_group_disjoint",
    "build_group_kfold_assignments",
    "fit_transform_train_only",
]
