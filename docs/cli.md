# CLI reference

The `verino` command (short alias `vrn`) is installed with the Python package in `tools/verino`.

## `verino pins check`

```bash
verino pins check hardware.yaml            # human report
verino pins check hardware.yaml --json     # same report as JSON
verino pins check hardware.yaml --write    # also fill reserved and validation
```

Runs every rule in [`chipdata/rules/rules.yaml`](../chipdata/rules/rules.yaml) on the file ([rules](rules.md)).

### Exit codes

| Code | Status | Meaning |
| --- | --- | --- |
| 0 | `ok` | no active errors or warnings |
| 1 | `warnings` | at least one active warning, no errors |
| 2 | `error` | at least one active error, or the file cannot be read |

Acknowledged findings (`ack`) are reported but do not change the status.

### Human output

One line per finding, in file order, then a summary:

```text
E-VOLT-001 hw.yaml:41:57 devices.tank.echo: hc-sr04 echo drives 5 V or more into GPIO16 (community source). esp32s3 pins accept at most 3.6 V; a direct connection can damage it. Fix: add a voltage divider or a level shifter, or use a 3.3 V part.
hw.yaml: error (1 errors, 0 warnings, 0 info, 0 acknowledged)
```

### JSON output (`verino-report/1`)

```json
{
  "schema": "verino-report/1",
  "file": "hw.yaml",
  "status": "error",
  "exit_code": 2,
  "counts": {"errors": 1, "warnings": 0, "info": 0, "acknowledged": 0},
  "findings": [
    {
      "id": "E-VOLT-001", "severity": "error", "file": "hw.yaml", "line": 41, "col": 57,
      "path": "devices.tank.echo", "message": "...", "why": "...", "fix": "...",
      "pin": "GPIO16", "device": "tank", "acknowledged": false, "ack_reason": null
    }
  ]
}
```

Output is deterministic: the same input gives byte-identical output.

### `--write`

Writes the tool-owned blocks into the file and reports on the written file:

- `reserved`: pins used by flash, octal PSRAM/flash, USB and the UART0 console.
- `validation`: tool version, chip data version, status, active error and warning IDs, and the content checksum ([format](hardware-yaml.md#tool-written-blocks)).

User fields, comments and key order are kept. Running `--write` twice gives the same file. A file with YAML or schema errors, or with an unknown module, is not written; the reason goes to stderr.

When the file changes after `--write`, `check` reports `W-VAL-001` until `--write` runs again.

## `verino pins render`

```bash
verino pins render hardware.yaml              # writes next to hardware.yaml
verino pins render hardware.yaml -o <project> # writes into <project>/gen/
verino pins render hardware.yaml --json
```

Runs `check` first. When the check reports an active error nothing is written and the exit code is 2; otherwise the files below are (re)written and the exit code is 0. All outputs go under `gen/` so the tool never overwrites a user's own `sdkconfig.defaults` or `partitions.csv`.

| File | Content |
| --- | --- |
| `gen/pins.hpp` | `constexpr int` constants in `namespace pins::<bus or device id>` (pin roles in upper case, plus `FREQ_HZ`, `BAUD`, `ADDR`). No includes; compiles in Arduino and ESP-IDF code. |
| `gen/sdkconfig.defaults` | Flash mode/frequency/size, PSRAM mode/speed, CPU frequency and the custom partition table, as ESP-IDF `CONFIG_*` lines. Values come from `memory`, falling back to the module data. |
| `gen/partitions.csv` | The partition table with explicit offsets (only when `memory.partitions` is set). |
| `gen/pinout.md` | Pin table (GPIO, user, role, origin, locked), reserved pins and partitions. |

Using the outputs in an ESP-IDF project rendered with `-o <project>`:

```cmake
# <project>/CMakeLists.txt, before include($ENV{IDF_PATH}/tools/cmake/project.cmake)
set(SDKCONFIG_DEFAULTS "sdkconfig.defaults;gen/sdkconfig.defaults")
```

`CONFIG_PARTITION_TABLE_CUSTOM_FILENAME` points at `gen/partitions.csv`, relative to the project root. Add `gen/` to the include path of the component that uses `pins.hpp`.

JSON output (`verino-render/1`): `file`, `written` (paths), `reason` (why nothing was written, or `null`) and the full check `report`.

## `verino pins solve`

```bash
verino pins solve hardware.yaml               # print proposed pins and reasons
verino pins solve hardware.yaml --write       # write them as {pin: GPIOn, origin: solver}
verino pins solve hardware.yaml --reassign    # also move unlocked origin: solver pins
verino pins solve hardware.yaml --json        # verino-solve/1
```

Fills every pin set to `auto` ([format](hardware-yaml.md#pins)). Pins already assigned stay where they are; `locked: true` pins never move, even with `--reassign`.

| Exit code | Meaning |
| --- | --- |
| 0 | solved, or nothing to solve |
| 2 | no solution, or the file has other errors (fix those first) |

### How pins are chosen

1. For each open slot every GPIO of the chip is tried, and the real rule set runs on the file with that one pin filled in. A pin that causes an error on the slot is rejected; warnings and infos lower its score.
2. Preferences add to the score: the SPI host's IO_MUX pin for `sclk`/`mosi`/`miso`/`cs` (+50), an RTC-capable pin for device pins when `uses` has `deep_sleep` (+20). Strapping pins and pins shared with USB, UART0 or JTAG cost −30 each; every accepted warning costs −100 and every info −10.
3. Slots are filled most-constrained first, candidates best-first, with branch-and-bound on the total score (at most 200 complete assignments). Each complete assignment is checked as a whole; the best one without errors wins. Ties go to the lower GPIO number, so the result is deterministic.

Each chosen pin is printed with its reasons:

```text
buses.spi2.sclk   GPIO12  SPI2 IO_MUX pin for CLK
devices.soil.pin  GPIO1   ADC1 channel 0
```

When a slot has no usable pin, the output counts why each GPIO was rejected:

```text
no pin satisfies device 'tank' (echo) at devices.tank.echo; all 45 GPIOs rejected (a pin can fail several rules):
  E-VOLT-001: 45
```

Board default pins are not used yet: they need board data (T8).
