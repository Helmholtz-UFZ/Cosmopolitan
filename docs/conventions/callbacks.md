# Callbacks

Callbacks connect user interactions to server-side logic. They are defined in the
same file as the page layout they belong to.

## Rules

- Use module-level `@callback` decorator — never `register_*_callbacks(app)` functions
- All imports at top level — no imports inside callback functions
- Use `prevent_initial_call=True` unless the callback must fire on page load
- Use `prevent_initial_call="initial_duplicate"` for landing page hydration callbacks
  (the ones triggered by `dcc.Store` data)
- Use `allow_duplicate=True` when multiple callbacks write to the same output
- Use `PreventUpdate` (not `return dash.no_update` for all outputs) when the callback
  should do nothing
- Use constants from `cosmopolitan_app/constants.py` for component IDs in
  Input/Output/State — never literal strings

## Callback Placement

- Page-specific callbacks go in the page file (`pages/*.py`), after the layout
- Global callbacks (navbar, error modal) go in `cosmopolitan_app/layouts.py` or
  `cosmopolitan_app/error_handling.py`
- Keep callbacks close to the layout they modify — no separate callback files

## Loading Overlay — Clientside Only

The shared loading overlay (`LOADING_OVERLAY_MODAL_SHARED_ID`) uses a two-callback
pattern: a fast callback opens it (`is_open=True`), a slow processing callback closes
it (`is_open=False`). The opening callback **must** be a `dash.clientside_callback`.

**Why:** With `allow_duplicate=True`, Dash does not guarantee execution order of
server-side callbacks targeting the same output. A server-side `show_loading` can fire
*after* the processing callback returns, leaving the overlay permanently stuck open.
Clientside callbacks execute instantly in the browser, guaranteeing the overlay opens
before the server roundtrip begins.

**No shared inputs:** Dash generates `allow_duplicate` callback IDs by hashing the
**inputs** (SHA-256 of all `Input()` specs joined together). If the clientside (open)
callback and the server-side (close) callback share the exact same inputs, Dash produces
identical callback IDs and raises an "already in use" error. The clientside callback must
use a **different set** of inputs — typically only the button click(s), while the
server-side callback includes an additional dummy/store input for differentiation.

**Debugging hash collisions:** The error message includes a hash suffix like
`output-id.prop@<hex>`. To identify *which* callback collides, compute the SHA-256 of
the dot-joined `Input()` specs (e.g.
`hashlib.sha256("btn-id.n_clicks.store-id.data".encode()).hexdigest()`) and match it
against the hash in the error. This pinpoints the exact pair of callbacks sharing inputs.

```python
# CORRECT — clientside, fires instantly in the browser
import dash

dash.clientside_callback(
    "function(n) { return true; }",
    Output(LOADING_OVERLAY_MODAL_SHARED_ID, "is_open", allow_duplicate=True),
    Input(SOME_BUTTON_ID, "n_clicks"),
    prevent_initial_call=True,
)

# The processing callback closes it when done
@callback(
    Output(LOADING_OVERLAY_MODAL_SHARED_ID, "is_open", allow_duplicate=True),
    ...
    Input(SOME_BUTTON_ID, "n_clicks"),
    prevent_initial_call=True,
)
def process(n_clicks, ...):
    # ... slow work ...
    return False  # closes overlay
```

```python
# WRONG — server-side show_loading races with the processing callback
@callback(
    Output(LOADING_OVERLAY_MODAL_SHARED_ID, "is_open", allow_duplicate=True),
    Input(SOME_BUTTON_ID, "n_clicks"),
    prevent_initial_call=True,
)
def show_loading(n_clicks):
    return True
```

**Multiple triggers:** For callbacks with several button inputs, check any non-null:

```python
dash.clientside_callback(
    """
    function() {
        for (var i = 0; i < arguments.length; i++) {
            if (arguments[i] != null) return true;
        }
        return false;
    }
    """,
    Output(LOADING_OVERLAY_MODAL_SHARED_ID, "is_open", allow_duplicate=True),
    Input(BUTTON_A_ID, "n_clicks"),
    Input(BUTTON_B_ID, "n_clicks"),
    prevent_initial_call=True,
)
```

## Identifying the Trigger

When a callback has multiple inputs, use `callback_context` to determine which
triggered it. **Never use `triggered[0]`** — Dash can batch multiple input changes
into a single callback invocation (e.g., a field change and a button click arriving
together). `triggered[0]` picks whichever input appears first in the callback
definition, silently ignoring the rest.

Build a set filtered by `value is not None` to handle both batching and
`prevent_initial_call="initial_duplicate"` (where all inputs appear in `triggered`
with null values on page load):

```python
from dash import callback_context

triggered_ids = {
    t["prop_id"].split(".")[0]
    for t in callback_context.triggered
    if t["value"] is not None
}

if SUBMIT_BUTTON_ID in triggered_ids:
    ...
elif CANCEL_BUTTON_ID in triggered_ids:
    ...
```

**Why `is not None`:** In multi-page apps, navigating to a page re-renders its
components. Dash fires callbacks with ALL inputs in `triggered`, but buttons that
were never clicked have `n_clicks: null`. Without the filter, the set would contain
every button on every page load.

**When `triggered[0]` is acceptable:** Only in callbacks with a single `Input()` where
batching is impossible. If there are two or more `Input()` entries, use the set.

## Navigation Pattern

Redirect by writing to the global `URL_ID` location component:

```python
@callback(
    Output(URL_ID, "pathname", allow_duplicate=True),
    Input(SOME_BUTTON_ID, "n_clicks"),
    prevent_initial_call=True,
)
def navigate(n_clicks):
    target_path = dash.page_registry["pages.target"]["path_template"]
    return target_path.replace("<job_id>", job_id)
```

**Testing note:** With clientside overlay callbacks, Dash callback chains may cascade
(e.g. a submit callback re-fires after a refresh, triggering a second refresh cycle).
Use overlay wait timeouts of at least 20s in Playwright tests to accommodate this.

## Dict-Style Outputs

When a callback has **5+ outputs**, use dict-style `output={}`, `inputs={}`, `state={}`
instead of positional arguments. This makes return values self-documenting and eliminates
the error-prone counting of tuple positions.

**Keys must be valid Python identifiers** (underscores, not hyphens). The HTML ID string
values are unaffected — only the dict keys need to be identifiers.

For complex forms with many dynamic outputs, use dict-style callback signatures:

```python
@callback(
    output={
        "field_a": Output("field_a", "value"),
        "field_b": Output("field_b", "valid"),
    },
    inputs={
        "submit": Input(SUBMIT_ID, "n_clicks"),
    },
    state={
        "field_a": State("field_a", "value"),
    },
)
def form_manager(**state):
    ...
    return {"field_a": new_value, "field_b": True}
```

For branches that only update a subset of outputs, use a `no_update` baseline helper:

```python
def _no_update_result():
    return {
        "field_a": no_update,
        "field_b": no_update,
        # ... all outputs default to no_update
    }

# In callback branch:
result = _no_update_result()
result.update({"field_a": new_value})
return result
```

Use this only when the number of outputs makes positional returns unwieldy.

## Notes

- The global error handler (`error_handling.handle_error`) catches unhandled exceptions
  in callbacks and shows the error modal via `set_props()`. Individual callbacks do not
  need to handle errors that are covered by `error_responds_dict`.
- `dash.no_update` skips updating a single output. `PreventUpdate` skips the entire
  callback.
