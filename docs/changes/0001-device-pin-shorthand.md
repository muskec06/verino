# 0001: Device pin shorthand

- **Status:** applied-pending-review
- **Date:** 2026-11-18
- **Design version:** 0.2
- **Phase / task:** Phase 0 / T2
- **Affects:** `docs/tr/architecture.md` → section "Donanım tanımı: hardware.yaml" (format rule 1 and the format example); `schemas/verino-hw-1.schema.json`

## What the design says

Format rule 1: every pin assignment carries `origin` (`schematic`, `user`, `board_default`, `solver`, `cubemx`). The same section's example writes device pins as bare strings: `cs: GPIO10`, `pin: GPIO4`, `pin: LED_RGB`.

## What we need instead

Both forms are accepted for **device** pins:

```yaml
devices:
  sd:   { part: sdcard, bus: spi2, cs: GPIO10 }                               # shorthand
  temp: { part: ds18b20, kind: onewire, pin: { pin: GPIO4, origin: schematic, locked: true } }
```

The shorthand is read as `{ pin: GPIO10, origin: user, locked: false }`. **Bus** pins (`sda`, `scl`, `sclk`, `mosi`, `miso`, `tx`, `rx`, ...) always use the full object with `origin`, as in the design example.

## Why

The rule and the example contradict each other. The shorthand keeps hand-written files short, and a pin a user types directly is a `user` assignment, so no information is lost. The solver and importers always write the full object.

## Impact

- Schema: device pin roles accept `pin_name | pin_assignment`; bus pins accept only `pin_assignment`.
- Model: `Device.pins` is always normalized to `PinAssignment`, so rules and the solver see one shape.
- Not breaking: every file valid under the design example stays valid.

## Questions for the design session

- Should bus pins also accept the shorthand (same `origin: user` default)?
