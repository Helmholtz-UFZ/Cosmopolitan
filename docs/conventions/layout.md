# Layout

Reusable layout components live in `cosmopolitan_app/layouts.py`. Pages compose
these to build their structure.

## Rules

- Every page uses one of two container layouts — never build custom page wrappers
- Use `create_header()` for page headers — never create raw header divs
- Job-scoped pages use the landing page pattern (spinner + store + callback hydration)
- Use `swap_classes()` from `cosmopolitan_app/utils.py` to dynamically change classes
  (e.g., header background based on job status)
- Always use `className` — never `class_name`

## Page Container Layouts

### Column layout (most pages)

Centered responsive column with white background, border, and rounded corners.

```python
from cosmopolitan_app.layouts import page_container_column_layout

content = [header, form, buttons]
layout = page_container_column_layout(content)
```

### Fullscreen layout (map/visualization pages)

Full-width, no border or rounding.

```python
from cosmopolitan_app.layouts import page_container_fullscreen_layout

content = [header, map_container]
layout = page_container_fullscreen_layout(content)
```

## Landing Page Pattern

For pages that load data based on a URL parameter (e.g., `/input/<job_id>`):

```python
from cosmopolitan_app.layouts import landing_page_layout_column

def layout(job_id):
    return landing_page_layout_column(
        "Page Title", HEADER_ID, JOB_ID_STORE, job_id, MAIN_CONTENT_ID
    )

@callback(
    [
        Output(HEADER_ID, "className", allow_duplicate=True),
        Output(f"{HEADER_ID}-subtitle", "children"),
        Output(MAIN_CONTENT_ID, "children"),
    ],
    [Input(JOB_ID_STORE, "data")],
    [State(HEADER_ID, "className")],
    prevent_initial_call="initial_duplicate",
)
def load_content(job_id, header_class_name):
    # Load job, build content, return (header_class, subtitle, content)
    ...
```

This pattern:
1. Renders a spinner immediately (fast page load)
2. Stores `job_id` in `dcc.Store`
3. A callback fires on store data, loads the real content
4. Header color is updated via `swap_classes()`

Use `landing_page_layout_fullscreen` for the fullscreen variant.

## Header

```python
from cosmopolitan_app.layouts import create_header

header = create_header("Title", "Subtitle", bg_color="bg-info", id=HEADER_ID)
```

- `bg_color` must be a Bootstrap background class (`bg-info`, `bg-secondary`, etc.)
- `id` is required when the header is updated by callbacks
- `create_header` generates `f"{id}-title"` and `f"{id}-subtitle"` sub-IDs

## Loading Overlay

A global modal that blocks user interaction during server-side work. Defined in
`cosmopolitan_app/layouts.py`:

```python
loading_overlay = dbc.Modal(
    dbc.ModalBody(
        [dbc.Spinner(size="lg"), html.H4("Loading...", className="text-center mt-3")],
        className="text-center",
    ),
    id=LOADING_OVERLAY_MODAL_SHARED_ID,
    is_open=False,
    backdrop="static",
    keyboard=False,
    centered=True,
    size="sm",
)
```

The overlay is rendered once in `app_layout()` and shared across all pages.
Opening **must** use a `dash.clientside_callback` — see
[Callbacks: Loading Overlay](callbacks.md#loading-overlay--clientside-only) for the
pattern and rationale.

**Critical:** The clientside (open) and server-side (close) callbacks must have
**different `Input()` sets**. Dash hashes the inputs to generate `allow_duplicate`
callback IDs — identical inputs produce the same hash and raise an "already in use"
error. If both callbacks naturally share the same inputs, add a dummy store/div as an
extra input to the server-side callback to differentiate them.

## Notes

- `page_container_column_layout` accepts an optional `main_content_id` parameter —
  only pass it if the container itself needs to be targeted by callbacks
- Static pages (like home) can build `layout` as a module-level variable
- Dynamic pages (like new_job) define `layout` as a function
