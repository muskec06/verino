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
