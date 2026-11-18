# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Design documents (design v0.2), Phase 0 plan, contribution and community files.
- Python package skeleton (`tools/verino`) with the `verino` / `vrn` CLI: `--version` and an empty `pins` command group.
- CI workflow: `lint` (ruff, mypy) and `test` (pytest) on Python 3.11 and 3.13, Ubuntu and Windows; DCO sign-off check on pull requests.
- `hardware.yaml` schema `verino-hw/1` (`schemas/verino-hw-1.schema.json`), typed model with line/column locations (`verino.model`), round-trip writing that keeps comments, examples in `examples/hw/` and a format reference (`docs/hardware-yaml.md`).
- Diagnostics `E-YAML-001` and `E-SCHEMA-001`.
