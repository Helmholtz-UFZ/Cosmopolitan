# `docs/` — Agent & Docs Layer

This directory holds the shared agent-facing documentation for COSMOPOLITAN: conventions,
reusable skills, an architecture overview, current project state, decision records, and a
durable knowledge base. It is checked into the repo so every contributor and coding agent
works from the same context.

The repository's entry points — [`AGENTS.md`](../AGENTS.md) (tool-neutral) and
[`CLAUDE.md`](../CLAUDE.md) (Claude-specific) — live at the **repo root** and point here.

## Structure

```text
docs/
├── README.md          — this file
├── architecture.md    — module map and how the pieces fit
├── project-state.md   — current priorities, recent changes, open questions
├── conventions/       — binding coding rules (one topic per file)
│   └── TEMPLATE.md    — template for new conventions
├── decisions/         — architectural decision records (ADRs)
│   └── 0001-template.md
├── skills/            — step-by-step procedures for the agent
│   └── TEMPLATE.md    — template for new skills
└── knowledge/         — durable explanatory pages (how concepts/systems work)
    ├── index.md       — knowledge map
    ├── log.md         — dated history of knowledge updates
    ├── concepts/      — durable concepts used across the codebase
    └── systems/       — major subsystems and how they interact
```

## What goes where

| Need | Put it in |
|------|-----------|
| A binding coding rule / anti-pattern | `conventions/` |
| A repeatable procedure for the agent | `skills/` |
| How a concept or subsystem works | `knowledge/` (concepts/ systems/) |
| Why a lasting choice was made | `decisions/` (ADRs) |
| The current state of active work | `project-state.md` |
| The high-level code map | `architecture.md` |

## Adding content

- **New convention:** copy [`conventions/TEMPLATE.md`](conventions/TEMPLATE.md), fill it in, and
  add it to the index in [`CLAUDE.md`](../CLAUDE.md) if it's important.
- **New skill:** copy [`skills/TEMPLATE.md`](skills/TEMPLATE.md) and add it to the Skills list in
  [`CLAUDE.md`](../CLAUDE.md).
- **New decision:** create `decisions/<NNNN>-<slug>.md` from
  [`decisions/0001-template.md`](decisions/0001-template.md). Write an ADR only when the rationale
  isn't already captured by a convention — don't duplicate.
- **New knowledge page:** add a file under `knowledge/concepts/` or `knowledge/systems/`, then
  list it in [`knowledge/index.md`](knowledge/index.md) and add a dated entry to
  [`knowledge/log.md`](knowledge/log.md).

## conventions/ vs knowledge/

Both hold durable material, so keep the line clear: `conventions/` states **what you must do**
(binding rules and anti-patterns); `knowledge/` explains **how something works** (concepts and
subsystems). When you learn something worth preserving, pick the one that fits — and per the
Memory Policy in [`CLAUDE.md`](../CLAUDE.md), don't start a machine-managed `MEMORY.md` log; these
are hand-curated pages.

## Conventions for this directory

- Markdown-native, one topic per file, cross-link with relative links.
- Keep high-level files short; push detail into focused convention pages.
- Don't duplicate the same explanation across files — state it once and link.
