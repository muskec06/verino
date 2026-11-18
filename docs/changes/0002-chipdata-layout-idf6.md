# 0002: Chip data layout and ESP-IDF v6 sources

- **Status:** applied-pending-review
- **Date:** 2026-11-18
- **Design version:** 0.2
- **Phase / task:** Phase 0 / T3
- **Affects:** `docs/tr/architecture.md` → section "Pin, modül ve kart modeli" ("Çip verisi (pin başına alanlar)" and "Veri kaynakları"); `docs/plan/phase0.md` → T3; `schemas/chipdata.schema.json`

## What the design says

Chip data is shown per pin: `GPIO12: { caps, pulls, drive, strap: {...}, boot_behavior, wake, errata, provenance }`. Valid pins, output mask, RTC/ADC channels and peripheral counts are extracted from ESP-IDF `soc_caps.h` and soc headers; strapping, flash/PSRAM pins and errata are hand-written with page references.

## What we need instead

1. **Two blocks per chip file instead of one per-pin map.**

   ```yaml
   schema: verino-chip/1
   chip: esp32s3
   soc_caps:      # written only by verino.chipdata.extract_soc_caps
     provenance: {kind: soc_caps, source: esp-idf@v6.1.1, commit: ..., files: [...]}
     gpio: {count: 49, valid: [...], output: [...]}
     adc: {adc1: {GPIO1: 0, ...}, adc2: {...}}
     rtc_io: {GPIO0: 0, ...}
     fixed_pins: {usb_dm: GPIO19, ...}
     macros: {SOC_I2C_NUM: 2, PCNT_LL_UNITS_PER_INST: 4, ...}
   manual:        # hand-written; every group carries provenance
     strapping: {GPIO45: {..., provenance: {kind: datasheet, source: ..., ref: "Table 3-1, p. 32"}}}
     spi_flash_pins: {...}
     boot_behavior: {...}
   ```

   Code merges both blocks into the per-pin view of the design.
2. **Peripheral counts are stored raw**, keyed by the ESP-IDF macro name (`SOC_SPI_PERIPH_NUM: 3`). Interpretation (for example which SPI hosts are general purpose) belongs to the rules, with its own provenance.
3. **ESP-IDF v6 moved some counts out of `soc_caps.h`.** PCNT and RMT counts now live in `components/esp_hal_pcnt/<chip>/include/hal/pcnt_ll.h` and `components/esp_hal_rmt/<chip>/include/hal/rmt_ll.h` (`PCNT_LL_UNITS_PER_INST`, `RMT_LL_CHANS_PER_INST`, ...). The extractor reads these headers too; provenance stays `soc_caps` and lists every file read.
4. **Sources are registered once** in `chipdata/sources.yaml` (title, version, URL, sha256 / commit) and cited by id.

## Why

- Regenerating the extracted part must never touch hand-written facts. With one per-pin map the tool would have to edit individual fields inside user-maintained entries; two blocks make regeneration a whole-block replacement (same approach as `reserved` / `validation` in `hardware.yaml`).
- Interpreting counts inside the extractor would put unsourced judgement into data marked `soc_caps`.
- ESP-IDF v6.1.1 was chosen as the extraction source (maintainer decision, 2026-11-18). Values were compared with v5.5.6 for ESP32 and ESP32-S3: the same PCNT/RMT counts appear in v5.5.6 `soc_caps.h`.

## Impact

- `schemas/chipdata.schema.json` describes `soc_caps` and `manual` separately.
- T4 rules read chip facts through a merged per-pin view (to be added with the first rule that needs it).
- Not breaking: no chip data existed before.

## Questions for the design session

- Should the per-pin presentation in the architecture document be updated to the two-block layout, or kept as the conceptual model?
