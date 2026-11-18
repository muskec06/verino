"""Derived files for ``verino pins render``: pins.hpp, sdkconfig fragment, partitions, pinout."""

from verino.render.outputs import (
    PARTITIONS_CSV,
    PINOUT_MD,
    PINS_HPP,
    SDKCONFIG,
    RenderResult,
    render,
    render_file,
)

__all__ = [
    "PARTITIONS_CSV",
    "PINOUT_MD",
    "PINS_HPP",
    "SDKCONFIG",
    "RenderResult",
    "render",
    "render_file",
]
