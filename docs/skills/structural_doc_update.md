# Structural Doc Update

After a major structural change lands, update the **smallest coherent set** of docs files
needed to keep the agent layer accurate. Treat this layer as living project memory.

## When to use

- After a change to: package/module structure, subsystem ownership, data/control flow, config
  or API semantics, durable conventions, entry points, or operational workflows.

**Not** for: local bug fixes, narrow refactors with unchanged semantics, test-only changes, or
tiny renames that don't change how the system is understood.

> Guiding rule: update the docs layer **only if** the change alters the mental model a future
> contributor or agent needs to work correctly.

## Steps

1. **Understand the change.** From the diff/commits: what changed structurally, which parts of
   the mental model are now stale, and which files are affected. Don't edit yet.
2. **Map to files** — update each only when its trigger is met:
   - root [`../../AGENTS.md`](../../AGENTS.md) — commands, layout, or entry points changed
   - [`../architecture.md`](../architecture.md) — component map, flow, patterns, or responsibilities changed
   - [`../project-state.md`](../project-state.md) — add a concise "now" entry if it matters for ongoing work
   - [`../conventions/`](../conventions/) — a binding rule changed or an example became wrong
   - [`../decisions/`](../decisions/) — the change reflects a lasting decision (write/supersede an ADR)
   - [`../../CLAUDE.md`](../../CLAUDE.md) — a project-wide rule, convention index, or skill list changed
3. **Plan the smallest patch.** Prefer patching existing pages over duplicating; prefer links
   over bloat.
4. **Apply edits.**
5. **Lint pass.** Check the touched files for contradictions, stale claims, missing cross-links,
   outdated paths, and duplicated explanations. Fix the obvious ones.
6. **Report** what you changed, what you deliberately left alone, and any follow-up needed.

## Verification

- No internal link is broken and no path is stale.
- No explanation is duplicated across files — it's stated once and linked.
- `AGENTS.md` stays a short index; `project-state.md` stays a "now" page.
