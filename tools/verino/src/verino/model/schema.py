"""JSON Schema validation of ``hardware.yaml`` with line/column mapping."""

from __future__ import annotations

import functools
import json
from collections.abc import Iterable, Sequence
from importlib import resources
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from verino.model.diagnostics import SCHEMA_ERROR, Diagnostic
from verino.model.types import Location

SCHEMA_FILE = "verino-hw-1.schema.json"

_REQUIRED_HINTS: dict[str, tuple[str, str]] = {
    "origin": (
        "Every bus pin records where it came from.",
        "add origin: user (or schematic, board_default, solver, cubemx).",
    ),
    "reason": (
        "An acknowledgement without a reason hides the decision from reviewers.",
        'add reason: "<why this is safe>".',
    ),
    "schema": ("Tools need the format version to read the file.", "add schema: verino-hw/1."),
    "module": (
        "Flash, PSRAM and module-internal pins come from the module.",
        "add module: <module id>, e.g. esp32-s3-wroom-1-n8r8.",
    ),
}


def _read_schema_text() -> str:
    packaged = resources.files("verino") / "schemas" / SCHEMA_FILE
    if packaged.is_file():
        return packaged.read_text(encoding="utf-8")
    # Editable/source checkout: the canonical file lives at <repo>/schemas/.
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "schemas" / SCHEMA_FILE
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
    raise FileNotFoundError(f"{SCHEMA_FILE} not found in the package or the repository")


@functools.cache
def load_schema() -> dict[str, Any]:
    schema: dict[str, Any] = json.loads(_read_schema_text())
    return schema


@functools.cache
def _validator() -> Draft202012Validator:
    return Draft202012Validator(load_schema())


def format_path(path: Sequence[str | int]) -> str:
    if not path:
        return "(root)"
    out = ""
    for part in path:
        if isinstance(part, int):
            out += f"[{part}]"
        else:
            out += f".{part}" if out else str(part)
    return out


def locate(doc: Any, path: Sequence[str | int], file: str, *, key: bool = False) -> Location:
    """Location of the value at ``path`` (or of its key when ``key`` is true)."""
    node = doc
    line, col = 0, 0
    for index, part in enumerate(path):
        lc = getattr(node, "lc", None)
        last = index == len(path) - 1
        try:
            if lc is not None:
                if isinstance(part, int):
                    line, col = lc.item(part)
                elif last and key:
                    line, col = lc.key(part)
                else:
                    line, col = lc.value(part)
            node = node[part]
        except (KeyError, IndexError, TypeError):
            break
    return Location(file, line + 1, col + 1)


def _pick(errors: Iterable[ValidationError]) -> ValidationError | None:
    """Most useful branch of a failed oneOf/anyOf: skip plain type mismatches, prefer depth."""
    candidates = [e for e in errors if e.validator != "type"]
    if not candidates:
        return None
    return max(candidates, key=lambda e: len(e.absolute_path))


def _is_pin_name_schema(schema: Any) -> bool:
    return isinstance(schema, dict) and schema == load_schema()["$defs"]["pin_name"]


def _describe(error: ValidationError, doc: Any, file: str) -> Diagnostic:
    path = list(error.absolute_path)
    validator = error.validator
    instance: Any = error.instance

    if validator in ("oneOf", "anyOf"):
        inner = _pick(error.context or [])
        if inner is not None:
            return _describe(inner, doc, file)

    loc = locate(doc, path, file)
    where = format_path(path)

    if validator == "required":
        required: list[str] = cast(list[str], error.validator_value)
        missing = next(r for r in required if r not in instance)
        why, fix = _REQUIRED_HINTS.get(missing, ("", f"add {missing}."))
        return Diagnostic(SCHEMA_ERROR, loc, where, f"missing required field '{missing}'", why, fix)

    if validator == "additionalProperties" and isinstance(instance, dict):
        allowed = error.schema.get("properties", {}) if isinstance(error.schema, dict) else {}
        extra = next((k for k in instance if k not in allowed), None)
        if extra is not None:
            return Diagnostic(
                SCHEMA_ERROR,
                locate(doc, [*path, extra], file, key=True),
                where,
                f"unknown field '{extra}'",
                "Unknown fields are rejected so typos are caught.",
                "remove it or check the spelling.",
            )

    if validator == "pattern" and _is_pin_name_schema(error.schema):
        return Diagnostic(
            SCHEMA_ERROR,
            loc,
            where,
            f"'{instance}' is not a valid pin name",
            "Pin names are canonical so rules and generated code agree.",
            "use GPIO<n> without leading zeros (GPIO4) or a board alias in capitals (LED_RGB).",
        )

    if validator == "const":
        return Diagnostic(
            SCHEMA_ERROR,
            loc,
            where,
            f"'{instance}' must be '{error.validator_value}'",
            "",
            f"use {error.validator_value}.",
        )

    if validator == "enum":
        choices = ", ".join(str(v) for v in cast(list[Any], error.validator_value))
        return Diagnostic(
            SCHEMA_ERROR, loc, where, f"'{instance}' is not allowed", "", f"use one of: {choices}."
        )

    if validator == "type":
        return Diagnostic(
            SCHEMA_ERROR,
            loc,
            where,
            f"expected {error.validator_value}, got {type(instance).__name__}",
            "",
            f"write a {error.validator_value} here.",
        )

    return Diagnostic(
        SCHEMA_ERROR, loc, where, error.message.rstrip("."), "", "see docs/hardware-yaml.md."
    )


def validate(doc: Any, file: str) -> list[Diagnostic]:
    """Validate a parsed document against ``verino-hw/1``; diagnostics are sorted."""
    diags = {_describe(e, doc, file) for e in _validator().iter_errors(doc)}
    return sorted(diags, key=Diagnostic.sort_key)
