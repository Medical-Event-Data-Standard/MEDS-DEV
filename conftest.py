"""Root conftest: inject common names into the doctest namespace.

The ``yaml_to_disk`` and ``pretty_print_directory`` packages each ship a pytest plugin that registers
``yaml_disk`` / ``print_directory`` / ``PrintConfig`` for use in doctests without explicit imports.
This file extends that pattern for ``Path``, ``json``, and pytest's ``caplog`` fixture, so doctests
that need to assert on log output can use the standard pytest mechanism without leaving the doctest.

Per-module behavioral fixtures still live in ``tests/conftest.py`` — this file only covers the
doctest namespace.
"""

import json
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _doctest_globals(doctest_namespace: dict, caplog: pytest.LogCaptureFixture) -> None:
    doctest_namespace["Path"] = Path
    doctest_namespace["json"] = json
    doctest_namespace["caplog"] = caplog
