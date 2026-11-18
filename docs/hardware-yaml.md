# `hardware.yaml` reference (`verino-hw/1`)

`hardware.yaml` describes one hardware revision: board, module, memory, buses and device connections. Software settings live elsewhere. The machine-readable definition is [`schemas/verino-hw-1.schema.json`](../schemas/verino-hw-1.schema.json); this page explains it. Examples: [`examples/hw/`](../examples/hw/).

The schema only checks structure. Whether a pin exists, is free or is safe at boot is decided by the rules (`verino pins check`).

## Top level

| Field | Required | Written by | Meaning |
| --- | --- | --- | --- |
| `schema` | yes | user | Always `verino-hw/1` |
| `source` | no | user | `native` (default). Other sources are not supported in Phase 0 |
| `board` | no | user | Board id, e.g. `esp32-s3-devkitc-1` |
| `board_rev` | no | user | Board revision, e.g. `v1.1` (selects board aliases) |
| `module` | yes | user | Module id, e.g. `esp32-s3-wroom-1-n16r8` (flash, PSRAM, internal pins) |
| `chip_rev` | no | user | Chip revision `vX.Y`, used by errata rules |
| `hw_rev` | no | user | Your own circuit revision |
| `uses` | no | user | On-chip resources the firmware uses: `wifi`, `ble`, `deep_sleep`. Missing means `[wifi]`; write `uses: []` if none (change note [0003](changes/0003-hardware-uses-field.md)) |
| `memory` | no | user | Flash, PSRAM, CPU frequency, partitions |
| `buses` | no | user / solver | Bus instances by name |
| `devices` | no | user / solver | Connected parts by name |
| `ack` | no | user | Intentionally accepted findings |
| `reserved` | no | **tools only** | Pins the tool reserved and why |
| `validation` | no | **tools only** | Last check result and checksum |

Unknown fields are errors everywhere, so typos are caught.

## Pins

A pin name is either canonical, `GPIO<n>` without leading zeros (`GPIO8`), or a board alias in capitals (`LED_RGB`, `BOOT`). Aliases are resolved from board data.

A **pin assignment** records where the pin came from:

```yaml
sda: {pin: GPIO8, origin: board_default, locked: false}
```

| Key | Meaning |
| --- | --- |
| `pin` | Pin name |
| `origin` | `schematic`, `user`, `board_default`, `solver` or `cubemx` |
| `locked` | `true`: the solver never changes this pin. Pins from a schematic are constraints, not suggestions |

Bus pins always use the full assignment. Device pins may also use the **shorthand** `pin: GPIO4`, which means `{pin: GPIO4, origin: user, locked: false}` (change note [0001](changes/0001-device-pin-shorthand.md)).

## `memory`

```yaml
memory:
  flash: {size: 16MB, mode: qio, freq: 80m, origin: module}
  psram: {size: 8MB, mode: octal, freq: 80m, origin: module}
  cpu_freq_mhz: 240
  partitions:
    preset: two_ota              # ESP-IDF built-in table, or:
    custom:
      - {name: nvs, type: data, subtype: nvs, size: 24K}
      - {name: storage, type: data, subtype: littlefs, size: rest}
```

- Sizes: `<n>K`, `<n>KB`, `<n>M`, `<n>MB` (1024-based). `rest` runs to the end of flash.
- `preset` is one of the ESP-IDF built-in tables `singleapp`, `singleapp_large`, `two_ota`, `two_ota_large` ([`chipdata/idf/partitions.yaml`](../chipdata/idf/partitions.yaml)). When `custom` is given it is the table and `preset` is ignored.
- Partitions are placed the way ESP-IDF places blank offsets: after the partition table at 0x8000, data partitions on 4 KB boundaries, app partitions on 64 KB boundaries. `E-MEM-001`, `E-MEM-002` and `E-MEM-003` check the result against the module.
- `flash.mode`: `qio`, `qout`, `dio`, `dout`. `psram.mode`: `quad`, `octal`. Frequencies: `<n>m` (MHz).
- `origin`: `module` (taken from module data) or `user`.
- Whether these values fit the module is checked by `verino pins check`.

## `buses`

Bus names are lower-case identifiers (`i2c0`, `spi2`, `uart1`). `kind` selects the fields:

| `kind` | Pins | Other fields |
| --- | --- | --- |
| `i2c` | `sda`, `scl` (both required) | `freq_hz`, `pullups` (`none`, `internal`, `external`, `external_4k7`, ...) |
| `spi` | `sclk` (required), `mosi`, `miso` | `host` (`SPI2`, ...) |
| `uart` | `tx` and/or `rx`, `rts`, `cts` | `baud` |

## `devices`

```yaml
devices:
  env:  {part: bme280, bus: i2c0, addr: 0x76}
  temp: {part: ds18b20, kind: onewire, pin: GPIO4}
  tank: {part: hc-sr04, kind: gpio, trig: GPIO15, echo: GPIO16}
```

| Key | Meaning |
| --- | --- |
| `part` | Part id (required) |
| `bus` | Name of a bus defined under `buses` |
| `kind` | For parts not on a bus: `adc`, `gpio`, `onewire`, `pwm` |
| `addr` | Bus address (integer; `0x76` is fine) |
| `freq_hz` | Device clock or PWM frequency |
| any other key | A pin role from the part manifest (`pin`, `cs`, `int`, `rst`, `trig`, `echo`, ...) whose value is a pin name or a pin assignment |

## `ack`

```yaml
ack:
  - {rule: W-BOOT-010, pin: GPIO0, reason: "External pull-down fitted"}
```

`rule` and a non-empty `reason` are required; `pin` or `device` narrow it down. Acknowledged findings are reported as "acknowledged", not hidden.

## Tool-written blocks

Tools write only `reserved` and `validation` and never change user fields; comments and key order are preserved. `verino pins check --write` fills both ([CLI reference](cli.md)).

```yaml
reserved:
  - {pins: GPIO26-GPIO32, why: flash}     # range, or a list of pin names
validation:
  tool: verino 0.1.0
  chipdata: esp32s3@2026.11
  status: ok                              # ok | warnings | error
  warnings: []
  checksum: "sha256:<64 hex digits>"
```

- `reserved`: flash, octal PSRAM/flash, USB and UART0 console pins of the module and chip.
- `validation.chipdata`: `<chip>@<version>`, the `version` of `chipdata/sources.yaml`.
- `validation.warnings`: the active error and warning IDs.
- `validation.checksum`: sha256 of the canonical JSON of the file without `reserved` and `validation`. Editing comments keeps it valid; changing any value makes `verino pins check` report `W-VAL-001`.

## Diagnostics

Problems are reported with a rule ID, file, line and column, what is wrong, why it matters and a fix:

```text
E-SCHEMA-001 hardware.yaml:8:10 buses.i2c0.sda: missing required field 'origin'. Every bus pin records where it came from. Fix: add origin: user (or schematic, board_default, solver, cubemx).
```

| ID | Meaning |
| --- | --- |
| `E-YAML-001` | The file is not valid YAML (including duplicate keys) |
| `E-SCHEMA-001` | The file does not match `verino-hw/1`, or refers to an undefined bus or device |

Hardware rules are listed in [rules.md](rules.md).
