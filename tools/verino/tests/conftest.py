"""Shared paths for tests."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = REPO_ROOT / "examples" / "hw"
VALID_EXAMPLES = sorted(EXAMPLES.glob("*.yaml"))
INVALID_EXAMPLES = sorted((EXAMPLES / "invalid").glob("*.yaml"))
