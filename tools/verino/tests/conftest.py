"""Shared paths for tests."""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = REPO_ROOT / "examples" / "hw"
VALID_EXAMPLES = sorted(EXAMPLES.glob("*.yaml"))
INVALID_EXAMPLES = sorted((EXAMPLES / "invalid").glob("*.yaml"))


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-golden",
        action="store_true",
        help="Rewrite tests/golden/ from the current output instead of comparing.",
    )
