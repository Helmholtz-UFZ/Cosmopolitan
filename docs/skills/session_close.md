# Session Close

Propose an update to [`../project-state.md`](../project-state.md) summarising what changed
during the current session. **Propose — never write — until the human confirms.**

## When to use

- At the end of a session that produced substantive changes (new conventions, completed work,
  architectural decisions, notable refactors).
- When the human says "run session_close", "close the session", or similar.

Skip it for sessions that only touched code with no impact on the project's "now" state.

## Steps

1. Gather the session's material changes from the working tree (not memory):
   - `git log` / `git diff --stat` since the last state update,
   - work that started, completed, or was abandoned,
   - new or substantially edited conventions / ADRs,
   - decisions recorded in conversation.
2. Sort each item into the four [`../project-state.md`](../project-state.md) sections:
   - **Current priorities** — promote finished items off; add newly-started work.
   - **Recent changes** — a dated bullet, newest first, matching the file's style.
   - **Open questions** — carry forward unresolved items; drop answered ones.
   - **Decisions made** — durable choices with a one-line rationale (large ones → an ADR in
     [`../decisions/`](../decisions/)).
3. Update the `Last updated:` line to today's date.
4. Show the proposal as a **unified diff** against `project-state.md`.
5. Ask: **"Apply this update? (yes / edit / no)"** — `yes` writes the file, `edit` revises and
   re-shows, `no` discards.
6. Do **not** commit or push — leave version control to the human.

## Verification

- The diff applies cleanly and `project-state.md` still reads as a "now" page, not a changelog.
- Every new bullet is a verifiable fact from the working tree, not a guess.
