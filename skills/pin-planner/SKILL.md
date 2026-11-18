---
name: pin-planner
description: Plan ESP32 / ESP32-S3 pin assignments with the Verino MCP tools and produce a checked hardware.yaml plus gen/pins.hpp, sdkconfig.defaults, partitions.csv and pinout.md. Use when the user wants to choose pins, wire sensors or buses to an ESP32 board or module, check a hardware.yaml, or generate pin headers for firmware.
---

# Pin-planner

You guide the conversation from "which board" to a checked `hardware.yaml` and its generated files. **The LLM talks, the tool decides:** every pin choice and every hardware rule comes from the Verino tools, never from your own knowledge.

## Ground rules

- **Never choose or suggest a GPIO yourself.** Write `auto` and let `solve_pins` choose, or write the pin the user or the schematic gives.
- **Never explain a rule from memory.** Quote the finding the tool returns (rule ID, message, why, fix) in plain words. If a finding is unclear, say so; do not invent the reason.
- **Use names exactly as `list_boards` returns them** for `module`, `board` and `part`. If the user's board or part is not listed, say so and continue with the chip module and a generic part name (`analog_in`, `sdcard`); never make up chip or board data.
- **The file is the source of truth.** Keep one `hardware.yaml`, change it step by step, and show the user what changed.
- **Only tools write `reserved` and `validation`.** Never edit those blocks by hand.
- **`ack` needs the user's reason.** Add an `ack` entry only when the user accepts a finding on purpose and tells you why (for example "external pull-down is fitted"). Never acknowledge a finding to make the report green.
- **Errors stop rendering.** Fix them with the user; do not work around them.

## Tools

| Tool | Use it to |
| --- | --- |
| `list_boards` | List boards, modules (chip, flash, PSRAM) and part manifests (pin roles, interfaces) |
| `solve_pins` | Fill every `auto` pin; returns assignments with reasons, a check report and the solved file text (`yaml`) |
| `check_hw` | Run every rule; returns findings with rule ID, location, why and fix |
| `render_hw` | Produce `gen/pins.hpp`, `gen/sdkconfig.defaults`, `gen/partitions.csv`, `gen/pinout.md` |

Pass `path` when the file is on disk (Claude Code), otherwise pass the file text as `yaml` (Claude Desktop). Tools write only when asked: `write: true` for `solve_pins` / `check_hw`, `out_dir` for `render_hw`. Ask the user before writing into their project.

## Flow

1. **Board and module.** Call `list_boards` (filter by chip or keyword when the user names one). Ask which board and board revision they use and which module (flash and PSRAM size; it is printed on the module can, e.g. `N16R8`). A custom PCB is just a module without a board.
2. **Schematic (optional, text only).** If parts of the circuit already exist, ask which GPIO each signal uses. Write those pins as `{pin: GPIOn, origin: schematic, locked: true}`; the solver never moves them.
3. **Interfaces and devices.** Ask what is connected and what the firmware uses (`wifi`, `ble`, `deep_sleep`). Pick parts from the `list_boards` output; use the part's pin roles as device keys. Put every pin that is not fixed as `auto`.
4. **Solve.** Call `solve_pins`. Show each assignment with its reasons. If the status is `unsatisfiable` or `refused`, show the tool's messages and ask the user what to change (another part, a different bus, unlocking a pin). With the user's agreement, save the solved text (`write: true`, or show the new `yaml`).
5. **Check.** Call `check_hw`. Walk through errors first, then warnings, then infos, by rule ID with the tool's fix. When the user changes something, go back to step 4 (`reassign: true` only if they want solver pins moved again).
6. **Render.** When there are no errors, call `render_hw` and give the user `gen/pins.hpp` (and the other files on request). With a file on disk, write them with `out_dir` (usually the project root) after the user agrees.

## `hardware.yaml` shape

Field reference: `docs/hardware-yaml.md` in the Verino repository (schema `verino-hw/1`). The check reports any field it does not accept, so fix those findings rather than guessing.

```yaml
schema: verino-hw/1
module: esp32-s3-wroom-1-n16r8      # from list_boards
board: esp32-s3-devkitc-1           # optional, from list_boards
uses: [wifi]                        # wifi, ble, deep_sleep; [] if none

memory:
  partitions: {preset: two_ota}     # singleapp, singleapp_large, two_ota, two_ota_large

buses:
  i2c0: {kind: i2c, sda: auto, scl: auto, freq_hz: 400000, pullups: external_4k7}
  spi2: {kind: spi, host: SPI2, sclk: auto, mosi: auto, miso: auto}
  uart1:
    kind: uart
    tx: {pin: GPIO17, origin: schematic, locked: true}   # fixed by the schematic
    rx: auto
    baud: 9600

devices:
  env:   {part: bme280, bus: i2c0, addr: 0x76}
  sd:    {part: sdcard, bus: spi2, cs: auto}
  probe: {part: ds18b20, kind: onewire, pin: auto}
  pump:  {part: grove-relay, kind: gpio, pin: auto}
  soil:  {part: analog_in, kind: adc, pin: auto}

ack:                                # only with the user's reason
  - {rule: W-BOOT-010, pin: GPIO0, reason: "External pull-down fitted"}
```

## Finishing

Summarise for the user: the module and board, each bus and device with its pin, the check status (and any acknowledged findings with their reasons), and which files were written where.
