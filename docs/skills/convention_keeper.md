# Convention Keeper

Audit the codebase for convention violations and fix them systematically.

## Prerequisites

- Read all convention files in `docs/conventions/` before auditing

## Steps

1. **Pick a convention to audit** — work through one convention at a time rather
   than checking everything at once

2. **Search for violations** — use grep/glob patterns specific to each convention:

   **Bootstrap Styling** (`docs/conventions/bootstrap_styling.md`):
   - `style={` — inline CSS without justifying comment
   - `class_name=` — should be `className=`
   - `style={"font-weight":` — should be `className="fw-bold"`
   - `style={"text-align":` — should be `className="text-center"` etc.

   **Callbacks** (`docs/conventions/callbacks.md`):
   - `register_.*_callbacks` — legacy pattern, should be module-level `@callback`
   - Callbacks missing `prevent_initial_call`

   **Logging** (`docs/conventions/logging.md`):
   - `logging\.(debug|info|warning|error)` without `extra={"tag":` — missing tag
   - `logging\.` instead of `log\.` — should use module-level logger
   - Callbacks or dynamic layouts without `log.info()` entry point

   **Error Handling** (`docs/conventions/error_handling.md`):
   - `except Exception` without `# noqa` — bare exception catch
   - `dict.get(` — check if defensive or legitimate dispatch

   **Environment Variables** (`docs/conventions/environment_variables.md`):
   - `os.getenv` or `os.environ` outside `config.py` — should use `config.py`
   - New env vars missing from `env_vars` list

   **Layout** (`docs/conventions/layout.md`):
   - `class_name=` — should be `className=`
   - Custom page wrappers instead of `page_container_*_layout`

   **HTML IDs**:
   - Literal string IDs in `Input()`, `Output()`, `State()` — should be constants
   - IDs on components not used in callbacks or tests — unnecessary

3. **Categorize findings** — for each violation:
   - Is it a clear violation to fix now?
   - Is it a known violation documented as "clean up later"?
   - Is it an edge case that needs a convention update?

4. **Fix clear violations** — apply fixes one convention at a time. Run tests after
   each batch of fixes.

5. **Report remaining items** — list known violations that need future cleanup and
   edge cases that need convention decisions.

## Verification

- All fixes pass: `./run_pytest.sh --no-services`
- No new violations introduced
- Known violations are documented in the convention's "Known Violations" section
