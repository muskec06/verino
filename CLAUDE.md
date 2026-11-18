@AGENTS.md

# Notes for Claude Code

- `AGENTS.md` (imported above) is the root instruction file. If anything here conflicts with it, `AGENTS.md` wins.
- At the start of a session, read `docs/plan/phase0.md` and find the next unticked task. Continue with it unless the user gives you something else.
- For any task touching more than one file, write a short plan first (plan mode, Shift+Tab). Do not change schemas, rule IDs or folder structure without the user's approval.
- Never produce chip/board data from memory. Ask the user for the datasheet/TRM PDF or the local ESP-IDF path, and extract `soc_caps.h` facts with a script. Anything you cannot source stays `TODO(verify)`.
- The user may converse in Turkish; reply in Turkish in chat, but everything you write into the repository is English (except `docs/tr/`).
- For ESP32 build/flash/crash work, use the user's `esp-platformio` skill if it is available.
- Summarize long command output (`pytest -q`, `ruff`); show full logs only on failure.
- End every task with a three-line summary: files changed, tests run, plan item ticked.
- Use `/change-note <title>` instead of editing design docs when implementation must differ from the design.
- Run `/handoff` before ending a session; it rewrites `docs/STATUS.md`.
