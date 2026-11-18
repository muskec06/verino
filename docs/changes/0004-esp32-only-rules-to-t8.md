# 0004: ESP32-only Level 1 rules move from T4 to T8

- **Status:** applied-pending-review
- **Date:** 2026-11-18
- **Design version:** 0.2
- **Phase / task:** Phase 0 / T4, T8
- **Affects:** `docs/plan/phase0.md` → T4 (Level 1 list) and T8; `docs/tr/architecture.md` → section "Donanım doğrulama kuralları" (Seviye 1 table)

## What the design says

T4 implements all Level 1 rules, including "input-only", "no internal pull" and "ADC2 + Wi-Fi", each with a trigger and a clean fixture. ESP32 chip data arrives in T8.

## What we need instead

- `E-IO-001` (output on an input-only pin), `E-PULL-001` (pull requested on a pin without internal pulls) and `E-ADC-002` (ADC2 unusable while Wi-Fi is on) are implemented, registered and given fixtures in **T8**, together with ESP32 data.
- T4 adds `W-ADC-003` for chips where ADC2 is shared with Wi-Fi through the driver's arbitration (ESP32-S3: reads may fail with `ESP_ERR_TIMEOUT`; source: ESP-IDF v6.1.1 `docs/en/api-reference/peripherals/adc/adc_oneshot.rst`, Hardware Limitations).

## Why

On ESP32-S3 every valid GPIO is output-capable and has internal pulls (`soc_caps` output mask; datasheet Table 2-1), so these rules can have no trigger fixture on the only T4 chip. Registering them without fixtures would break principle 4.

## Impact

- T4 can be ticked with every registered rule having both fixtures.
- T8 must re-check `E-ADC-002`: the same ESP-IDF v6.1.1 document lists ESP32 next to ESP32-S2/S3 as "ADC2 is also used by Wi-Fi ... protection provided", so on ESP32 the correct rule may be `W-ADC-003`, not an error.

## Questions for the design session

- Confirm the ADC2 + Wi-Fi severity per chip once ESP32 data is in (T8).
