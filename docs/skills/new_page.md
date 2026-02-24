# New Page

Checklist for adding a new page to the Dash application.

## Prerequisites

- Read `docs/conventions/layout.md`, `docs/conventions/callbacks.md`,
  `docs/conventions/bootstrap_styling.md`
- Decide: column layout (most pages) or fullscreen layout (map/visualization)
- Decide: static layout (variable) or dynamic layout (function with parameters)

## Steps

1. **Create the page file** — `cosmopolitan_app/pages/<page_name>.py`

2. **Write the module docstring** — this is displayed on the documentation page.
   End with `NOTE: This docstring is displayed on the documentation webpage.`
   ```python
   """Short description of the page.

   Longer description of what the page does and its features.

   NOTE: This docstring is displayed on the documentation webpage.
   """
   ```

3. **Add top-level imports** — all imports at module level, never inside functions:
   ```python
   import logging

   import dash
   import dash_bootstrap_components as dbc
   from dash import Input, Output, State, callback, html

   from cosmopolitan_app.constants import ...
   from cosmopolitan_app.layouts import create_header, page_container_column_layout

   log = logging.getLogger(__name__)
   ```

4. **Register the page**:
   ```python
   # Simple path
   dash.register_page(__name__, path="/my_page")

   # Parameterized path
   dash.register_page(__name__, path_template="/my_page/<job_id>")
   ```

5. **Add component IDs to constants** — only for components used in callbacks,
   tests, or `set_props()`. Add to `cosmopolitan_app/constants.py`:
   ```python
   # My Page
   MY_PAGE_HEADER_ID = "my-page-header"
   MY_PAGE_MAIN_CONTENT_ID = "my-page-main-content"
   ```

6. **Build the layout**:

   For static pages:
   ```python
   header = create_header("Title", "Subtitle", bg_color="bg-info")
   layout = page_container_column_layout([header, content])
   ```

   For job-scoped pages (with loading spinner):
   ```python
   def layout(job_id):
       return landing_page_layout_column(
           "Title", HEADER_ID, JOB_ID_STORE, job_id, MAIN_CONTENT_ID
       )
   ```

7. **Add callbacks** — below the layout, using module-level `@callback`:
   ```python
   @callback(
       Output(...),
       Input(...),
       prevent_initial_call=True,
   )
   def my_callback(...):
       log.info("Description of action", extra={"tag": "frontend"})
       ...
   ```

8. **Add navbar link** — in `cosmopolitan_app/layouts.py` inside `create_navbar()`:
   ```python
   dbc.NavItem(
       dbc.NavLink(
           "My Page",
           href=dash.page_registry["pages.my_page"]["relative_path"],
       )
   ),
   ```

9. **Regenerate documentation** — run `cosmopolitan_app/doc_generator.py` to include
   the new page's docstring in the documentation page.

## Verification

- Page loads without errors at its URL
- Navbar link works
- All callbacks fire correctly
- `check_all_errors()` passes if you add an E2E test
- No literal ID strings — all from `constants.py`
- No inline `style={}` without justifying comment
- Every callback has `log.info()` with `extra={"tag": ...}`
