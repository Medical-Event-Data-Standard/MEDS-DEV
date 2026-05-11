"""Root conftest: inject common names into the doctest namespace.

The ``yaml_to_disk`` and ``pretty_print_directory`` packages each ship a pytest plugin that registers
``yaml_disk`` / ``print_directory`` / ``PrintConfig`` for use in doctests without explicit imports.
This file extends that pattern for ``Path``, ``json``, and ``capture_log_to_stdout`` so module-level
doctests don't have to spend their first line on boilerplate imports / setup.

Per-module behavioral fixtures still live in ``tests/conftest.py`` — this file only covers the
doctest namespace.
"""

import contextlib
import json
import logging
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest


@contextlib.contextmanager
def capture_log_to_stdout(logger_name: str, level: int = logging.INFO) -> Iterator[None]:
    """Route a logger to ``sys.stdout`` so its messages are visible in doctest output.

    Doctests don't have pytest's ``caplog`` fixture; assertions on log output have to round-trip
    through stdout. This context manager attaches a temporary handler at the given level, then
    detaches it when the block exits. The formatter is ``"<LEVEL>: <message>"`` so doctest output
    lines look like ``WARNING: Content mismatch ...``.
    """
    target_logger = logging.getLogger(logger_name)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    handler.setLevel(level)
    old_level = target_logger.level
    target_logger.addHandler(handler)
    target_logger.setLevel(level)
    try:
        yield
    finally:
        target_logger.removeHandler(handler)
        target_logger.setLevel(old_level)


@pytest.fixture(autouse=True)
def _doctest_globals(doctest_namespace: dict) -> None:
    doctest_namespace["Path"] = Path
    doctest_namespace["json"] = json
    doctest_namespace["capture_log_to_stdout"] = capture_log_to_stdout
