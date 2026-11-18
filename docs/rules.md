# Rules

The catalog is [`chipdata/rules/rules.yaml`](../chipdata/rules/rules.yaml): ID, severity, short name, summary, level, phase and the chip data each rule reads. Implementations live in `tools/verino/src/verino/rules/checks/` (one module per ID).

## IDs

- `E-` error, `W-` warning, `I-` info. The prefix always matches the severity.
- IDs are stable: a published ID is never reused or redefined.
- Every rule has `chipdata/rules/fixtures/<ID>/trigger.yaml` (must produce the ID on the line marked `# <- <ID>`) and `clean.yaml` (must not produce it). Tests enforce both.

## Acknowledging a finding

```yaml
ack:
  - {rule: W-RSV-003, pin: GPIO43, reason: "Console moved to USB; UART0 drives the RS-485 transceiver"}
```

A matching finding is still reported, marked `[acknowledged: <reason>]`, and does not count for the status. An `ack` that matches nothing is reported as `I-ACK-001`.

## Status

| Status | Meaning | `verino pins check` exit code |
| --- | --- | --- |
| `ok` | no active findings except info | 0 |
| `warnings` | at least one active warning | 1 |
| `error` | at least one active error | 2 |

## Unsolved pins

`E-PIN-005` reports every pin still set to `auto`. Other rules skip those slots; `verino pins solve` fills them ([CLI](cli.md#verino-pins-solve)).

## Memory rules

`E-MEM-001` (partitions fit in flash), `E-MEM-002` (OTA layout complete) and `E-MEM-003` (flash/PSRAM match the module) read `memory` in `hardware.yaml`, the module's memory data and the ESP-IDF partition facts in `chipdata/idf/partitions.yaml`. `W-VAL-001` reports a `validation` block whose checksum no longer matches the file.

## Python API

```python
from verino.model import load_hardware
from verino.rules import check

report = check(load_hardware("hardware.yaml"))
for finding in report.findings:
    print(finding)
```
