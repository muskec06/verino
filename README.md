# Verino

**Verified hardware layer for embedded agents: pins, drivers and data you don't have to guess.**

Verino is an open-source toolkit for ESP32 (and later STM32) firmware that lets humans and LLM agents plan hardware, generate code and reuse drivers **without guessing**. Every pin rule, chip fact and driver carries its source and its verification status.

> **Status: Phase 0 (pin-planner), pre-alpha.** Nothing is released yet. APIs, schemas and file formats will change.

## Why

- Pin mistakes (strapping pins, flash/PSRAM pins, ADC2 + Wi-Fi, 5 V devices) don't fail at compile time. The board just doesn't boot, or a device silently misbehaves.
- LLM agents write firmware fast but hallucinate register bits and pin facts.
- There are many drivers for the same sensor, with different APIs and unknown test status.

Verino's answer: **the LLM talks, deterministic tools decide.** Hardware knowledge lives in versioned data with provenance, rules have stable IDs and tests, and drivers state exactly where they were verified.

## What's in it (planned)

| Product | What it does | Phase |
| --- | --- | --- |
| **Hardware toolkit** | Chip/board data, `hardware.yaml`, `verino pins check / solve / render`, MCP server, pin-planner skill | 0 (now) |
| **Driver kit** | Chip-independent C++17 HAL, `RegisterDevice`, typed register maps, native drivers with fake-model or trace tests | 1 |
| **Catalog** | Verification matrix (chip × board × SDK), measured flash/RAM cost, agent index | 0b / 2 |

## Quick look (Phase 0 target)

```bash
pip install verino            # not published yet
verino pins check hardware.yaml
```

```text
E-STRAP-002  hardware.yaml:42  GPIO12 is a strapping pin. A DS18B20 pull-up holds it HIGH at reset,
             which selects 1.8 V flash and the module will not boot.
             Fix: use GPIO13 or GPIO14.
```

## Documentation

- [Architecture overview](docs/architecture.md)
- [Phase 0 plan](docs/plan/phase0.md)
- [Architecture decision records](docs/adr/)
- [Full architecture document (Turkish)](docs/tr/architecture.md)
- [Contributing](CONTRIBUTING.md) · [Agent instructions](AGENTS.md)

## Supported hardware (Phase 0)

ESP32-S3 (ESP32-S3-DevKitC-1) and ESP32 (ESP32-DevKitC). ESP32-C3 and Seeed XIAO ESP32-S3 follow in Phase 0b. STM32 support is planned for Phase 3.

## License

[Apache-2.0](LICENSE). Website: [verino.dev](https://verino.dev)
