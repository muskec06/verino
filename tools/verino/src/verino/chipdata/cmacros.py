"""Read object-like ``#define`` macros from C headers and evaluate integer expressions.

Only a small, safe subset of C is accepted: integer literals (``U``/``L`` suffixes are
dropped), ``BITn``, other macros, parentheses and the operators ``| & ^ ~ << >> + - *``.
Anything else raises :class:`MacroError` so that an unexpected header change is noticed
instead of silently producing a wrong value. Python's ``eval`` is never used.
"""

from __future__ import annotations

import ast
import operator
import re
from collections.abc import Callable, Mapping

_DEFINE = re.compile(r"^\s*#\s*define\s+([A-Za-z_]\w*)(\(?)(.*)$")
_INT = re.compile(r"\b(0[xX][0-9a-fA-F]+|\d+)[uUlL]*\b")
_BIT = re.compile(r"^BIT(\d{1,2})$")

_BIN_OPS: dict[type[ast.operator], Callable[[int, int], int]] = {
    ast.BitOr: operator.or_,
    ast.BitAnd: operator.and_,
    ast.BitXor: operator.xor,
    ast.LShift: operator.lshift,
    ast.RShift: operator.rshift,
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
}
_UNARY_OPS: dict[type[ast.unaryop], Callable[[int], int]] = {
    ast.Invert: operator.invert,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


class MacroError(ValueError):
    """A macro is missing or uses syntax outside the supported subset."""


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", text)


def parse_defines(text: str) -> dict[str, str]:
    """Object-like macros of a header as ``{name: replacement text}``, in file order."""
    joined = re.sub(r"\\\r?\n", " ", _strip_comments(text))
    defines: dict[str, str] = {}
    for line in joined.splitlines():
        match = _DEFINE.match(line)
        if match is None or match.group(2) == "(":
            continue  # not a define, or a function-like macro
        defines[match.group(1)] = " ".join(match.group(3).split())
    return defines


def evaluate(expr: str, defines: Mapping[str, str]) -> int:
    """Evaluate a macro name or an integer expression using ``defines``."""
    return _evaluate(expr, defines, ())


def _evaluate(expr: str, defines: Mapping[str, str], stack: tuple[str, ...]) -> int:
    source = _INT.sub(lambda m: str(int(m.group(1), 0)), expr).strip()
    if not source:
        raise MacroError("empty expression")
    try:
        tree = ast.parse(source, mode="eval")
    except SyntaxError as exc:
        raise MacroError(f"unsupported expression: {expr!r}") from exc
    return _node(tree.body, expr, defines, stack)


def _node(node: ast.AST, expr: str, defines: Mapping[str, str], stack: tuple[str, ...]) -> int:
    if isinstance(node, ast.Constant) and type(node.value) is int:
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left = _node(node.left, expr, defines, stack)
        right = _node(node.right, expr, defines, stack)
        return _BIN_OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_node(node.operand, expr, defines, stack))
    if isinstance(node, ast.Name):
        return _name(node.id, defines, stack)
    raise MacroError(f"unsupported expression: {expr!r}")


def _name(name: str, defines: Mapping[str, str], stack: tuple[str, ...]) -> int:
    if name in stack:
        raise MacroError(f"recursive macro: {' -> '.join((*stack, name))}")
    if name in defines:
        return _evaluate(defines[name], defines, (*stack, name))
    bit = _BIT.match(name)
    if bit is not None:
        return 1 << int(bit.group(1))
    raise MacroError(f"macro {name} is not defined")
