# Design sync process

Verino's design is produced in **design sessions** (a separate Claude chat with the maintainer) and implemented in **coding sessions** (Claude Code in this repository). This file defines how the two stay in sync without loading the whole design into every coding session.

## Ownership

| Path | Owner | Coding sessions may |
| --- | --- | --- |
| `docs/architecture.md`, `docs/tr/`, `docs/adr/`, `docs/design/` | Design session | Read only. Propose changes via change notes |
| `docs/plan/phaseN.md` | Design session writes tasks | Tick tasks, add to "TODO(verify)" and "Parked" |
| `docs/changes/` | Coding session | Create and update change notes |
| `docs/STATUS.md` | Coding session | Rewrite at the end of every session (`/handoff`) |
| Code, schemas, data, tests | Coding session | Everything, within the current phase |

Typo fixes and broken links in design docs may be fixed directly.

## Code → design: change notes

Whenever implementation needs to differ from the design (a schema field changes, a rule is split, an API shape changes, a task turns out impossible), the coding session **does not edit the design docs**. It writes a change note:

- File: `docs/changes/NNNN-short-title.md` (next free number), from `docs/changes/TEMPLATE.md`.
- Status: `proposed` → `accepted` / `rejected` → `incorporated` (design docs updated).
- Small, local decisions that do not touch any design doc need no note; mention them in `STATUS.md` instead.
- If the change blocks work, the coding session may implement it immediately with status `applied-pending-review`.

## Session handoff: `docs/STATUS.md`

At the end of every coding session (`/handoff`), `docs/STATUS.md` is rewritten (not appended) with: design version in use, phase and current task, tasks completed since last sync, change notes waiting for review, open questions for the design session, risks. It stays under ~80 lines. This single file plus the new change notes is everything a design session needs.

## Design sync

1. Maintainer brings `docs/STATUS.md` and the new/updated change notes to the design session (or lets the design session read the repository directly).
2. The design session answers questions, accepts/rejects change notes, updates design docs, writes ADRs, and prepares the next phase plan.
3. The design session returns files (a zip or a PR) that bump the design version in `docs/DESIGN_VERSION`.
4. Maintainer commits them as `docs: design sync vX.Y` and sets incorporated notes to `incorporated`.

## Keeping coding sessions small

- `CLAUDE.md` / `AGENTS.md` stay short and phase-scoped.
- Only the current phase plan is read by default. Future-phase design lives in `docs/design/` and is read only when a task links to it.
- Completed phase plans move to `docs/plan/archive/`.
