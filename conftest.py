"""Root conftest: inject common names into the doctest namespace.

The ``yaml_to_disk`` and ``pretty_print_directory`` packages each ship a pytest plugin that registers
``yaml_disk`` / ``print_directory`` / ``PrintConfig`` for use in doctests without explicit imports.
This file extends that pattern for ``Path``, ``json``, and two log-related helpers:

- pytest's ``caplog`` fixture, for assertion-style checks on log records.
- ``capture_log_to_stdout``, a context manager that routes a logger to ``sys.stdout`` so log
    messages appear inline in the doctest output. Use this when the log message is part of the
    documented contract — readers see the actual log line, not just a programmatic assertion that
    one was emitted.

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
    """Route a logger to ``sys.stdout`` for the duration of the context.

    Output lines are formatted as ``<LEVEL>: <message>`` so they're easy to match in doctests via
    ELLIPSIS for the variable parts.
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
def _doctest_globals(doctest_namespace: dict, caplog: pytest.LogCaptureFixture) -> None:
    doctest_namespace["Path"] = Path
    doctest_namespace["json"] = json
    doctest_namespace["caplog"] = caplog
    doctest_namespace["capture_log_to_stdout"] = capture_log_to_stdout
