"""Tests for the restricted C macro reader used by the soc_caps extractor."""

import pytest

from verino.chipdata.cmacros import MacroError, evaluate, parse_defines

S3_MASK = "(0x1FFFFFFFFFFFFULL & ~(0ULL | BIT22 | BIT23 | BIT24 | BIT25))"


def test_parse_object_like_defines_and_skip_function_like() -> None:
    text = (
        "#pragma once\n"
        "#define A (1)  // comment\n"
        "#define B  2U /* block */\n"
        "#define F(x) ((x) + 1)\n"
        "#define LONG \\\n    (3)\n"
        "/* #define HIDDEN 9 */\n"
    )
    assert parse_defines(text) == {"A": "(1)", "B": "2U", "LONG": "(3)"}


def test_real_s3_valid_gpio_mask() -> None:
    value = evaluate(S3_MASK, {})
    assert value == (1 << 49) - 1 - sum(1 << n for n in (22, 23, 24, 25))
    assert [n for n in range(49) if not value >> n & 1] == [22, 23, 24, 25]


def test_macro_chains_resolve() -> None:
    defines = {"MASK": S3_MASK, "OUT": "(MASK & ~(BIT0))"}
    assert evaluate("OUT", defines) == evaluate(S3_MASK, {}) & ~1


@pytest.mark.parametrize(
    ("expr", "expected"),
    [("(2U)", 2), ("0x10", 16), ("1 << 4", 16), ("(-1)", -1), ("8UL >> 1", 4), ("3 + 4", 7)],
)
def test_simple_expressions(expr: str, expected: int) -> None:
    assert evaluate(expr, {}) == expected


@pytest.mark.parametrize(
    "expr",
    ["UNKNOWN_MACRO", "f(1)", "1 / 2", "'a'", "(uint64_t)1", "1 if 1 else 2", ""],
)
def test_unsupported_expressions_raise(expr: str) -> None:
    with pytest.raises(MacroError):
        evaluate(expr, {})


def test_recursive_macro_is_rejected() -> None:
    with pytest.raises(MacroError, match="recursive"):
        evaluate("A", {"A": "B", "B": "A"})
