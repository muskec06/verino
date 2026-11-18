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
