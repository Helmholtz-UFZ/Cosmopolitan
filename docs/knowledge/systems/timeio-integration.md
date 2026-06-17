# TimeIO / STA Integration (CRNS data)

The cosmic-ray neutron sensor (CRNS) measurements that feed predictions come from an external
**SensorThings API (STA)** hosted at UFZ ("TimeIO" / "STI" in the code). This is the app's only
measurement data source. The integration lives in
[`timeio_manager.py`](../../../cosmopolitan_app/timeio_manager.py) with a static device registry in
[`timeio_info.py`](../../../cosmopolitan_app/timeio_info.py).

## The API

`TimeIOManager` is a classmethod-based client against a fixed SensorThings base URL:

```
https://tsm.ufz.de/sta/crnscosmicrayneutronsens_<…>/v1.1
```

It uses standard STA resources — `Things`, `Datastreams`, `Locations`, `Observations` — via
`requests` (120 s timeout, `HTTPError`/`RequestException` handling). Key methods: `get_things`,
`get_datastreams_of_thing`, `get_location_of_thing`, `collect_datastreams`, `get_values`,
`is_stationary`, and `check_things`.

## Device registry (`timeio_info.py`)

The API exposes Things by numeric id; the app maps those ids with **hard-coded dictionaries**:

- `type_id_dict` — Thing id → `"station"` or `"train"` (drives `is_stationary`).
- `thing_datastream_dict` — Thing id → {datastream id → name} (e.g. `"Neutron counts"`,
  `"latitude"`, `"longitude"`). Mobile (train) things carry lat/long datastreams; stationary ones
  generally just neutron counts.
- `thing_info_dict` — Thing id → human-readable name (e.g. `44: "CRNS - Hohes Holz 4m"`).
- `ignore_things = [145, 219]` — Things deliberately skipped.

> **Gotcha:** these dictionaries are a manually maintained mirror of the API. `check_things()`
> compares the live API against the registry and **logs a warning** ("New things found in STI API.
> Please update the timeio_info table …") when they drift. New sensors do **not** flow in
> automatically — the registry must be edited.

## Updating measurements

`update_crns_measurments()` is the refresh entry point (run nightly by the `update_db` Beat task —
see [`job-lifecycle.md`](job-lifecycle.md) — or manually via
`background_job_manager.submit_update_db_task()`):

- Reads `start_date` / `end_date` from the `app_config` table. If `start_date` is `None`, it
  **skips**. If `end_date` is `None` or later than yesterday, it clamps to yesterday.
- Transfers data **day by day** (`transfer_data_by_day`).
- `maintenance_tasks.update_db_task` records each run in the `update_db_runs` table with the
  worker PID (used to scope log filtering), marking it `completed` / `failed`.

`repopulate_crns_measurements()` exists for a full reload.

## Mobile-point reduction

For moving sensors (trains/rovers), raw GPS-tagged observations are collapsed to representative
points: `GeoProximityTracker` (haversine distance + a proximity threshold) and
`find_representative_points_mobile` / `find_representative_points_stationary`. This keeps the
stored measurement set from exploding while preserving spatial coverage.

## Related

- [`job-lifecycle.md`](job-lifecycle.md) — the `update_db` maintenance task that drives refreshes
- [`soil-moisture-prediction.md`](soil-moisture-prediction.md) — consumer of these measurements
- Code: [`timeio_manager.py`](../../../cosmopolitan_app/timeio_manager.py), [`timeio_info.py`](../../../cosmopolitan_app/timeio_info.py), [`test/test_update_measurements.py`](../../../test/test_update_measurements.py)
