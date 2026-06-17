# Soil-Moisture-Prediction (SMP) Integration

`soil-moisture-prediction` ("SMP") is the **external library that does the actual prediction** —
COSMOPOLITAN is the web/orchestration layer around it. SMP is a hard dependency
(`soil-moisture-prediction>=0.1.0,<0.2` in [`pyproject.toml`](../../../pyproject.toml)), and the
app is coupled to it in three concrete places, so changes in SMP can break the app silently.

## How the app invokes SMP

A computation worker calls it as a CLI entry point
([`tasks/computation_tasks.py`](../../../cosmopolitan_app/tasks/computation_tasks.py)):

```python
from soil_moisture_prediction.smp_cli import main as smp_main
rfo_model = smp_main(verbosity="debug", work_dir=job.working_dir)
```

SMP reads its inputs from and writes its outputs into the job's `working_dir`. It returns the
trained random-forest object (`rfo_model`); `None` means the run failed → the job is marked
`FAILED` (see [`job-lifecycle.md`](job-lifecycle.md)).

## The three coupling points

1. **Form model inherits SMP's parameters.** `ModelWebsite`
   ([`pydantic_models.py`](../../../cosmopolitan_app/pydantic_models.py)) subclasses
   `soil_moisture_prediction.pydantic_models.InputParameters`. Most form fields
   (`area_*`, `monte_carlo_*`, `projection`, …) come straight from SMP; COSMOPOLITAN only adds
   web-specific fields (`email`, `job_id`, uploads, CRNS source toggles). New SMP parameters
   appear in the form automatically via [`../concepts/dynamic-forms.md`](../concepts/dynamic-forms.md).
2. **Predictor streams come from SMP.** `stream_dic` is imported from
   `soil_moisture_prediction.input_data`; the form's `pred_streams` choices are
   `list(stream_dic.keys())`, and `stream_dic[stream].class_info(stream)` provides the
   human-readable descriptions shown in the UI.
3. **Pinned assumptions.** [`test/test_smp_assumptions.py`](../../../test/test_smp_assumptions.py)
   asserts `stream_dic` contains the expected entries (see below). If SMP renames or drops a
   stream, this test fails first — that's the intended early-warning signal.

## Predictor streams

Stream keys follow the SoilGrids-style pattern `<property>_<depth>`, plus the elevation model
`elevation_bkg`. The pinned set:

- **Properties:** `bdod`, `cec`, `cfvo`, `clay`, `nitrogen`, `phh2o`, `sand`, `silt`, `soc`,
  `ocd`, `ocs`.
- **Depths:** `0-5cm`, `5-15cm`, `15-30cm`, `30-60cm`, `60-100cm`, `100-200cm`.
- Plus `elevation_bkg`. The form default is `["elevation_bkg", "bdod_5-15cm"]`.

> **Gotcha (from the test's own comment):** the results page only knows `elevation_bkg` as an
> elevation model. Adding a new elevation stream in SMP requires matching work in
> `get_available_map_types` on the results side, or the new model won't render.

## Local development against SMP

By default the worker and webserver use the **PyPI** SMP release. To develop against a local
checkout, use the `--local-smp` flag:

```bash
./dev_up.sh --local-smp <mock|prod|stage>   # expects ../soil-moisture-prediction (sibling dir)
```

Under the hood this layers in [`docker-compose.local-smp.yml`](../../../docker-compose.local-smp.yml),
which bind-mounts the sibling repo `../soil-moisture-prediction` into the containers and **prepends
it to `PYTHONPATH`**, shadowing the installed version for both webserver and worker.

> **Stale filename caveat:** `dev_up.sh` references the correct file `docker-compose.local-smp.yml`
> (hyphen), but `docker_local_smp_up.sh` and the README's raw `docker compose` examples reference
> `docker-compose.local_smp.yml` (**underscore**), which does not exist — those invocations fail.
> Prefer `./dev_up.sh --local-smp`. The `SOIL_MOISTURE_PREDICTION_PATH` env var mentioned in the
> README is real (read by `docker_local_smp_up.sh`) but the `/home/andersj/...` default path is a
> leftover personal path.

## Related

- [`job-lifecycle.md`](job-lifecycle.md) — where `smp_main()` runs in the overall flow
- [`../concepts/dynamic-forms.md`](../concepts/dynamic-forms.md) — how SMP parameters become form fields
- [`timeio-integration.md`](timeio-integration.md) — the CRNS measurements fed into a prediction
- Code: [`pydantic_models.py`](../../../cosmopolitan_app/pydantic_models.py), [`tasks/computation_tasks.py`](../../../cosmopolitan_app/tasks/computation_tasks.py), [`test/test_smp_assumptions.py`](../../../test/test_smp_assumptions.py)
