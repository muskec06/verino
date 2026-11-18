# Chip and module data

Hardware knowledge lives in `chipdata/` as YAML; code reads it. The structure is defined by [`schemas/chipdata.schema.json`](../schemas/chipdata.schema.json). Layout decisions: change note [0002](changes/0002-chipdata-layout-idf6.md).

```text
chipdata/
  sources.yaml          # documents and source trees cited by the data
  chips/<chip>.yaml     # verino-chip/1
  modules/<module>.yaml # verino-module/1
  parts/<part>.yaml     # verino-part/1
  rules/rules.yaml      # verino-rules/1 (see rules.md)
```

## Rules

- **No invented facts.** Every value comes from ESP-IDF headers or a cited document. If a value cannot be confirmed, write `TODO(verify)` and list it under "TODO(verify)" in `docs/plan/phase0.md` as `` `<file>` `<dotted.path>` `` with the reason. A test enforces the listing.
- **Provenance on every hand-written group.** `provenance: {kind, source, ref, note?}`:
  - `kind`: `soc_caps`, `datasheet`, `errata`, `community` or `measured`;
  - `source`: an id from `chipdata/sources.yaml`, e.g. `esp32s3-datasheet@2.2`;
  - `ref`: section, table and printed page, e.g. `Table 3-1 (p. 32)`.
- **Sources are pinned.** `sources.yaml` records title, version, URL and the PDF sha256 or the ESP-IDF commit. PDFs are not stored in the repository.

## Chip files

```yaml
schema: verino-chip/1
chip: esp32s3
soc_caps:   # generated; do not edit
  provenance: {kind: soc_caps, source: esp-idf@v6.1.1, idf_version: v6.1.1, commit: ..., files: [...]}
  gpio: {count: 49, valid: [...], output: [...]}
  adc: {adc1: {GPIO1: 0, ...}, adc2: {...}}   # GPIO -> channel
  rtc_io: {GPIO0: 0, ...}                     # GPIO -> RTC IO channel
  fixed_pins: {usb_dm: GPIO19, usb_dp: GPIO20, uart0_tx: GPIO43, uart0_rx: GPIO44}
  macros: {SOC_I2C_NUM: 2, PCNT_LL_UNITS_PER_INST: 4, ...}   # raw ESP-IDF values
manual:     # hand-written
  strapping: {GPIO45: {function, default, boot_safe, on_violation, severity, provenance}}
  spi_flash_pins / octal_spi_pins / usb_pins / uart0_pins / jtag_pins: {pins: {GPIOn: SIGNAL}, note?, provenance}
  boot_behavior: {pins: {GPIOn: {state, pull, glitches?, note?}}, provenance}
```

- `boot_behavior.state`: `hi_z`, `pulled_high`, `pulled_low` or `pulses` (any power-up glitch).
- `macros` are stored under their ESP-IDF names without interpretation; the rules decide what a count means.

## Module files

```yaml
schema: verino-module/1
module: esp32-s3-wroom-1-n16r8
chip: esp32s3
manual:
  part_number: {value, provenance}
  memory: {flash: {size, interface, max_freq_mhz}, psram: {size, interface, in_package}, vdd_spi_volts, provenance}
  exposed_gpios: {pins: [...], provenance}       # GPIOs that reach module pads
  internal_pins: {pins: {GPIOn: use}, note, provenance}   # pads used inside the module
```

## Part files

Minimal device manifests used by the boot and voltage rules (Phase 0).

```yaml
schema: verino-part/1
part: grove-relay
title: Seeed Studio Grove - Relay v1.2
manual:
  interface: {kinds: [gpio], provenance}
  supply: {min_volts, max_volts, provenance}                # optional
  pins: {roles: {pin: {direction: input|output|open_drain, level?: supply|pullup}}, provenance}
  reset_imposes: {roles: {pin: pulled_high|pulled_low|none}, note?, provenance}   # level at power-up
  actuator: {value: true, safe_boot_level: low|high, note?, provenance}
```

- Role names match the device keys in `hardware.yaml` (`pin`, `trig`, `echo`, ...).
- `reset_imposes` includes parts the datasheet requires (e.g. the DS18B20 pull-up on DQ).
- Parts without a manufacturer datasheet use `kind: community` (HC-SR04).

## Regenerating `soc_caps`

Requires an ESP-IDF v6 source tree with `components/soc`, `components/esp_hal_pcnt`, `components/esp_hal_rmt` and `components/esp_common/include`:

```bash
cd tools/verino
python -m verino.chipdata.extract_soc_caps --idf <esp-idf> --chip esp32s3 --out ../../chipdata/chips/esp32s3.yaml
VERINO_IDF_PATH=<esp-idf> pytest tests/test_chipdata.py   # checks the committed block matches the tree
```

The extractor replaces only the `soc_caps` block and keeps `manual` and comments. It fails loudly when a header or macro is missing or uses C syntax it does not understand.
