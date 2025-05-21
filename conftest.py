"""Test set-up and fixtures code."""

import tempfile
from typing import Any

import pytest


@pytest.fixture(autouse=True)
def __MEDS_transforms_setup_doctest_namespace(
    doctest_namespace: dict[str, Any],
):
    doctest_namespace.update(
        {
            "tempfile": tempfile,
        }
    )
