# 0006: `auto` pins, `E-PIN-005` and solver inputs

- **Status:** applied-pending-review
- **Date:** 2026-11-18
- **Design version:** 0.2
- **Phase / task:** Phase 0 / T6
- **Affects:** `docs/tr/architecture.md` → `hardware.yaml` format (pin assignment), "Otomatik atama (`verino pins solve`)"; MCP tool `solve_pins`

## What the design says

`verino pins solve` takes the board, the requested interfaces/devices and the `locked` pins, and returns assignments with a reason for each. Every pin assignment in `hardware.yaml` is `{pin, origin, locked?}`; the solver writes `origin: solver`. How a request without pins is written is not specified.

## What we need instead

- Any pin slot (bus pin or device pin) may be the string `auto`: `sda: auto`, `cs: auto`, `pin: auto`. `verino pins solve --write` replaces each `auto` with `{pin: GPIOn, origin: solver}`.
- New rule `E-PIN-005` (error): a pin is still `auto`. `check` reports it and `render` refuses the file. Other rules skip `auto` slots.
- By default the solver fills only `auto` slots and keeps every assigned pin. `--reassign` also frees unlocked `origin: solver` pins. `locked: true` pins are never moved.
- Chip data gains `soc_caps.spi_iomux` (quad-mode IO_MUX pins per SPI host), extracted from ESP-IDF `esp_hal_gpspi/<chip>/include/soc/spi_pins.h`.
- Reasons are reported by the command (human and JSON); no comments are written into `hardware.yaml`.

## Why

- Keeping the request in `hardware.yaml` keeps one source of truth: the same file is checked, solved, checked again and rendered, and the MCP tool can build it the same way.
- Without `E-PIN-005` an unsolved file would pass `check` silently or fail with misleading pin errors.
- The IO_MUX preference needs the pin numbers as sourced data (principle 3), not constants in code.

## Impact

- `verino-hw/1` accepts `auto` where a pin is expected; files without `auto` are unaffected.
- Bus pins now accept a bare string (`auto` only), a small step toward the bus shorthand asked about in 0001.

## Questions for the design session

- Should bus pins also accept a bare GPIO name (0001), now that they accept `auto`?
- Should solver reasons be kept in the file (e.g. a tool-written `solver` block) for later review?
