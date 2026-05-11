"""Root conftest: inject common names into the doctest namespace.

The ``yaml_to_disk`` and ``pretty_print_directory`` packages each ship a pytest plugin that registers
``yaml_disk`` / ``print_directory`` / ``PrintConfig`` for use in doctests without explicit imports.
This file extends that pattern for ``Path`` and ``json`` so module-level doctests don't have to spend
their first line on ``>>> from pathlib import Path`` etc.

Per-module behavioral fixtures still live in ``tests/conftest.py`` — this file only covers the
doctest namespace.
"""

import json
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _doctest_globals(doctest_namespace: dict) -> None:
    doctest_namespace["Path"] = Path
    doctest_namespace["json"] = json
