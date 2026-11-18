# Contributing to Verino

Thanks for your interest! Verino is in **Phase 0 (pre-alpha)**, so the most valuable contributions right now are hardware data, rule fixtures and real-world feedback.

## Good first contributions

- **Chip, module or board data** with datasheet references (see "Hardware data rules" below).
- **Rule fixtures:** a `trigger.yaml` / `clean.yaml` pair that exercises a rule.
- **Bug reports** with a minimal `hardware.yaml`.
- **Hardware verification reports** (later phases): run the tool on your board and report the result.

Look for issues labelled `good first issue` and `hardware-data`.

## Scope

Please read [`AGENTS.md`](AGENTS.md) → "Out of scope in Phase 0" before opening a large PR. Out-of-scope ideas are welcome as issues or Discussions; they go to the "Parked" list in [`docs/plan/phase0.md`](docs/plan/phase0.md).

## Hardware data rules

A wrong pin fact is worse than a missing one.

- Every hand-written fact carries `provenance` (`datasheet`, `errata`, `community`, `measured`; `soc_caps` is generated).
- `datasheet` and `errata` facts cite the document name, revision and page or section.
- `community` facts can produce warnings at most; they become errors only after they are `measured`.
- If you are not sure, leave the value out and open an issue.

## Development setup

```bash
git clone https://github.com/muskec06/verino   # will move to verino-dev/verino
cd verino/tools/verino
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest && ruff check . && mypy src/verino
```

## Pull requests

- One topic per PR; link the issue or plan task (e.g. `T4`).
- Tests first: every new rule has a `rules.yaml` entry and both fixtures.
- Schema changes update `schemas/`, fixtures and docs in the same PR.
- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat(rules): add E-STRAP-002`).
- Changes that conflict with a design principle need an ADR in `docs/adr/`.

## Developer Certificate of Origin (DCO)

We use the [DCO](https://developercertificate.org/) instead of a CLA. Sign off every commit:

```bash
git commit -s -m "feat(rules): add E-STRAP-002"
```

This adds `Signed-off-by: Your Name <you@example.com>` and certifies that you have the right to submit the work under the project's license (Apache-2.0).

## AI-assisted contributions

AI tools are welcome; this project is built with them. You remain responsible for every line: run the tests, check hardware facts against the cited sources, and say in the PR description which parts were AI-generated.

## Community

- Questions and ideas: GitHub Discussions.
- Bugs and data corrections: GitHub Issues (use the templates).
- Behaviour: see [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).
