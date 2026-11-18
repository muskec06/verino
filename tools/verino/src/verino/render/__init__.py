"""Derived files for ``verino pins render``: pins.hpp, sdkconfig fragment, partitions, pinout."""

from verino.render.outputs import (
    PARTITIONS_CSV,
    PINOUT_MD,
    PINS_HPP,
    RENDER_SCHEMA,
    SDKCONFIG,
    RenderResult,
    render,
    render_file,
    render_loaded,
    to_dict_result,
    write_outputs,
)

__all__ = [
    "PARTITIONS_CSV",
    "PINOUT_MD",
    "PINS_HPP",
    "RENDER_SCHEMA",
    "SDKCONFIG",
    "RenderResult",
    "render",
    "render_file",
    "render_loaded",
    "to_dict_result",
    "write_outputs",
]
