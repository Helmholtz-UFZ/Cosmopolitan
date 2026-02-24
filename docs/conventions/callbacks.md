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

## Loading Overlay Pattern

Most pages show a loading overlay while server-side work runs. The pattern:

```python
@callback(
    Output(LOADING_OVERLAY_ID, "is_open", allow_duplicate=True),
    Input(SOME_BUTTON_ID, "n_clicks"),
    prevent_initial_call=True,
)
def show_loading(n_clicks):
    if n_clicks:
        return True
    return False
```

The overlay is closed by the main callback that does the actual work (returning
`False` for the overlay output).

## Identifying the Trigger

When a callback has multiple inputs, use `callback_context` to determine which
triggered it:

```python
from dash import callback_context

triggered_id = callback_context.triggered[0]["prop_id"].split(".")[0]

if triggered_id == SUBMIT_BUTTON_ID:
    ...
elif triggered_id == CANCEL_BUTTON_ID:
    ...
```

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

## Dict-Style Outputs

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

Use this only when the number of outputs makes positional returns unwieldy.

## Notes

- The global error handler (`error_handling.handle_error`) catches unhandled exceptions
  in callbacks and shows the error modal via `set_props()`. Individual callbacks do not
  need to handle errors that are covered by `error_responds_dict`.
- `dash.no_update` skips updating a single output. `PreventUpdate` skips the entire
  callback.
