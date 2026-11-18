# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Design documents (design v0.2), Phase 0 plan, contribution and community files.
- Python package skeleton (`tools/verino`) with the `verino` / `vrn` CLI: `--version` and an empty `pins` command group.
- CI workflow: `lint` (ruff, mypy) and `test` (pytest) on Python 3.11 and 3.13, Ubuntu and Windows; DCO sign-off check on pull requests.
