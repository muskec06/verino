---
description: End-of-session handoff; rewrite docs/STATUS.md for the next design sync
---
Prepare the session handoff.

1. Read `docs/STATUS.md`, `docs/plan/phase0.md` (or the current phase plan) and `docs/changes/README.md`.
2. Check `git log` since the last `docs: design sync` commit for what was done.
3. Rewrite `docs/STATUS.md` (do not append) following its existing headings: design version (from `docs/DESIGN_VERSION`), phase, current task, done since last design sync, change notes awaiting review, open questions for the design session, risks/blockers. Keep it under 80 lines, factual, no prose padding.
4. If any implementation decision deviated from the design without a change note, create the note first (same rules as `/change-note`).
5. Finally print the list of files the maintainer should bring to the design session: `docs/STATUS.md` plus change notes that are `proposed` or `applied-pending-review`.
