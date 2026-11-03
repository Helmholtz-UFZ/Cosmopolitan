# TimeIO / STA Integration (CRNS data)

The cosmic-ray neutron sensor (CRNS) measurements that feed predictions come from an external
**SensorThings API (STA)** hosted at UFZ ("TimeIO" / "STI" in the code). This is the app's only
measurement data source. The integration lives in
[`timeio_manager.py`](../../../cosmopolitan_app/timeio_manager.py); the device registry is the `timeio_info` table.

## The API

`TimeIOManager` is a classmethod-based client against a fixed SensorThings base URL:

```
https://tsm.ufz.de/sta/crnscosmicrayneutronsens_<…>/v1.1
```

It uses standard STA resources — `Things`, `Datastreams`, `Locations`, `Observations` — via
`requests` (120 s timeout, `HTTPError`/`RequestException` handling). Key methods: `get_things`,
`get_datastreams_of_thing`, `get_location_of_thing`, `collect_datastreams`, `get_values`,
`is_stationary`, and `check_things`.

## Device registry (`timeio_info` table)

The API exposes Things by numeric id; the app maps those ids with the Postgres table
`timeio_info` (read through `PostgresManager.get_timeio_*`, wrapped by `TimeIOManager`):

- sensor type (`station`, `train`, ...) and the computed `stationary` flag,
- datastream id → name (e.g. `"Neutron counts"`, `"latitude"`, `"longitude"`). Mobile (train)
  things carry lat/long datastreams; stationary ones generally just neutron counts,
- the human-readable name (e.g. `44: "CRNS - Hohes Holz 4m"`),
- the `ignored` flag for Things deliberately skipped.

Sensors are added and edited through the sensor management page, not in code.

> **Gotcha:** the table is a manually maintained mirror of the API. `check_things()` compares
> the live API against it and **raises** ("New things found in STI API. Please update the
> timeio_info table …") when a Thing is missing. New sensors do **not** flow in automatically.

## Updating measurements

`update_crns_measurments()` is the refresh entry point (run nightly by the `update_db` Beat task —
see [`job-lifecycle.md`](job-lifecycle.md) — or manually via
`submissions.submit_update_db_task()`):

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
- Code: [`timeio_manager.py`](../../../cosmopolitan_app/timeio_manager.py), [`test/test_update_measurements.py`](../../../test/test_update_measurements.py)
