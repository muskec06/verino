# 0003: `uses` field in hardware.yaml

- **Status:** applied-pending-review
- **Date:** 2026-11-18
- **Design version:** 0.2
- **Phase / task:** Phase 0 / T4
- **Affects:** `docs/tr/architecture.md` → section "Donanım tanımı: hardware.yaml" (format `verino-hw/1`); `schemas/verino-hw-1.schema.json`; `docs/hardware-yaml.md`

## What the design says

`hardware.yaml` holds board, module, memory, buses, pins and devices; software settings (network, polling) live in `project.yaml`. Rules and the solver nevertheless depend on radio and sleep use: "ADC2 + Wi-Fi" (Level 1), "Wi-Fi varsa ADC1, deep sleep varsa RTC pini" (solver preferences).

## What we need instead

An optional top-level list of hardware resources the firmware will use:

```yaml
uses: [wifi, ble, deep_sleep]
```

- Allowed values: `wifi`, `ble`, `deep_sleep`.
- Missing field: treated as `[wifi]` (conservative); ADC2 findings then suggest adding `uses: []` when Wi-Fi is not used.

## Why

`verino pins check` and `solve` read only `hardware.yaml`; `project.yaml` does not exist in Phase 0. A CLI flag would make the same file pass or fail depending on how it is invoked. The field describes which on-chip hardware is taken by the radio or sleep logic, so it belongs next to the pin plan.

## Impact

- Schema, model (`HardwareSpec.uses`), reference doc and examples updated together. Additive, not breaking.
- Phase 1 `project.yaml` may later derive or check this field.

## Questions for the design session

- Should `project.yaml` own this in Phase 1, with `hardware.yaml` keeping a generated copy?
