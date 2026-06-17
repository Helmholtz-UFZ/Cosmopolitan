# Dynamic Forms (Pydantic → dash-form-factory)

The job-submission form is **generated from a Pydantic model, not hand-built**. The model
`ModelWebsite` is the single source of truth for fields, defaults, widgets, and validation; the
`dash-form-factory` library turns it into Dash components. This is why adding a job parameter is
usually a model edit, not a UI edit — and it's how SMP's parameters surface automatically (see
[`../systems/soil-moisture-prediction.md`](../systems/soil-moisture-prediction.md)).

## The pieces

- **The model:** `ModelWebsite` in
  [`pydantic_models.py`](../../../cosmopolitan_app/pydantic_models.py), a subclass of SMP's
  `InputParameters`. Each field is `Annotated[...]` with a `Field(...)` whose
  `json_schema_extra={"type": <widget>}` selects the widget.
- **The library:** `dash_form_factory` provides `FormFactory` and `InputField`
  ([`form_template_factory.py`](../../../cosmopolitan_app/form_template_factory.py)).
- **The layout:** `generate_template()` returns a Dash component tree of Bootstrap cards/rows
  (`_make_card`) seeded with `InputField("<field_name>")` **placeholders** (e.g.
  `InputField("email")`, `InputField("date_range")`, `InputField("pred_streams")`,
  `InputField("area_x1")`). `dash-form-factory` resolves each placeholder against `ModelWebsite`,
  rendering the right widget with the model's default, title, and description.

## Widget types

Set per field via `json_schema_extra["type"]`. Types in use: `email`, `text`, `date-picker`,
`dropdown-checklist` (e.g. `pred_streams`), `file-upload` / `multiple-file-upload`, and
`checkbox` (the `train_data` / `station_data` / `rover_data` toggles).

## Validation lives in the model (server-side)

Pydantic validators run on submit and feed field-level error messages back to the form:

- `validate_job_id` — `^\w+$`, length 8–50.
- `check_email` — allows empty; otherwise `email-validator` with deliverability check.
- `check_date_range` — both `YYYY-MM-DD`, start ≤ end.
- `check_soil_moisture_data` (a `model_validator`) — enforces **exactly one** CRNS source: either
  pick built-in sources (`train`/`station`/`rover`) **or** upload CRNS data, not both / neither.
  It raises `PydanticCustomError` with a `loc_tuple` so the error attaches to the right fields.
- `model_config = ConfigDict(validate_assignment=True)` — re-validates on every attribute set, so
  a `ModelWebsite` can never hold an invalid `job_id`.

## Rendering selected inputs

`construct_selected_input()` builds a Bootstrap `ListGroup` summarizing the chosen predictors and
CRNS sources for review. Uploaded predictors show coverage; coverage **≤ 50 %** is flagged with
`text-danger`. Predictor-stream descriptions come from `stream_dic[stream].class_info(stream)`.

## Conventions to respect here

- **HTML IDs via constants only.** Dynamically-built id keys (e.g. `self.job_id_key`) carry a
  `# nocheck` comment per [`../../conventions/html_ids.md`](../../conventions/html_ids.md).
- **Bootstrap, not inline CSS.** The few inline styles here are `white-space: pre-line` (no
  Bootstrap equivalent) and each is justified with a comment — the documented escape hatch in
  [`../../conventions/bootstrap_styling.md`](../../conventions/bootstrap_styling.md).

## Do / Don't

- **Do** add a new job parameter by adding the field to `ModelWebsite` and an
  `InputField("<name>")` placeholder in `generate_template()`.
- **Don't** hand-build Dash `dcc.Input`/`dbc` widgets for model-backed fields — you lose the
  validation and the single source of truth.

## Related

- [`../systems/soil-moisture-prediction.md`](../systems/soil-moisture-prediction.md) — why most fields come from SMP's `InputParameters`
- [`../systems/job-lifecycle.md`](../systems/job-lifecycle.md) — what happens after the form validates
- [`../../conventions/html_ids.md`](../../conventions/html_ids.md), [`../../conventions/layout.md`](../../conventions/layout.md), [`../../conventions/callbacks.md`](../../conventions/callbacks.md)
- Code: [`pydantic_models.py`](../../../cosmopolitan_app/pydantic_models.py), [`form_template_factory.py`](../../../cosmopolitan_app/form_template_factory.py)
