# `cosmo-suite@v0.4.0` — was sich für COSMOPOLITAN ändert

**Quelle:** `cosmo-suite/docs/plan/slice1b-framework-batch2.md`, umgesetzt am 2026-08-06.
**Status dieser App:** pinnt weiter `v0.3.0`. Re-Pin erst, wenn das eigene Slice 1b
durch ist. Bis dahin ändert sich hier **nichts** — diese Datei ist die Checkliste für
den Moment des Re-Pins.

Batch 2 hat die sechs Punkte hochgezogen, an denen COSMONAUT die Framework-Version
lokal umgehen musste. Drei davon ändern Verhalten, das diese App bisher **stillschweigend
geerbt** hat. Genau die stehen zuerst.

---

## Muss angefasst werden (sonst Regression)

### 1. `ModelWebsite` muss auf `UploadJobConfig` wechseln — **breaking**

`BaseJobConfig` ist aufgespalten:

| Klasse | Felder |
|---|---|
| `BaseJobConfig` | `job_id` + `validate_assignment=True` |
| `UploadJobConfig(BaseJobConfig)` | zusätzlich `upload_file_name` |

`cosmopolitan_app/pydantic_models.py:32` (`class ModelWebsite(InputParameters,
BaseJobConfig)`) **verliert `upload_file_name`**, wenn es beim Re-Pin nicht auf
`UploadJobConfig` wechselt. Der Docstring darunter benennt das Feld ausdrücklich als
Beitrag von `BaseJobConfig` — der Satz muss mit.

Kein Importfehler, kein Testfehlschlag beim Import: Pydantic akzeptiert das Modell
ohne das Feld, es fällt erst dort auf, wo etwas `model.upload_file_name` liest.

Grund für die Aufspaltung: `upload_file_name` gehört zum Nutzungsmuster des
Framework-`Job`, nicht zum Minimalvertrag. COSMONAUTs `JobTable` hat dafür keine
Spalte, `save()` brach daran (gemessen).

### 2. Celery-Zeitlimits sind weg — **wenn hier ein Limit gewollt ist, jetzt setzen**

`BaseCeleryConfig` hatte `task_soft_time_limit = 3600` / `task_time_limit = 3900`.
Beide stehen jetzt auf `None`.

`cosmopolitan_app/celery_config.py` überschreibt sie **nicht** (geprüft) — diese App
hat die Limits also bisher unbemerkt geerbt und verliert sie mit dem Re-Pin
ersatzlos. Ein durchgedrehter Task läuft danach unbegrenzt.

**Entscheidung dieser App:** entweder explizit in der eigenen `CeleryConfig` setzen
(dann mit gemessener Begründung, wie lange eine große CRNS-Prediction wirklich
läuft), oder bewusst ohne Limit fahren. Beides ist in Ordnung — stillschweigend
verlieren ist es nicht.

Grund für die Änderung: das Limit traf in COSMONAUT genau die großen Surveys, für
die die App existiert (Sensor-Routing ist O(n²), nicht kachelbar).

### 3. `get_files()` überschreibt nicht mehr bedingungslos — **`job.py:249` prüfen**

```python
get_files(dirname, *, overwrite=False, timeout=600)
```

`overwrite=False` (der neue Default) fährt `--ignore-existing`: nur lokal fehlende
Dateien werden geholt. `overwrite=True` ist das alte Verhalten (`--checksum`).

Diese App hat ihren lokalen `object_storage_manager` in Slice 1 gelöscht und ruft
die Framework-Funktion direkt:

- `cosmopolitan_app/job.py:249` → `get_files(self.job_id)` — **hier entscheiden**
- `cosmopolitan_app/job.py:646` → `save_files(self.job_id)` — unverändert

Die Frage, die nur die Domäne beantworten kann: lädt `job.py:249` Dateien zum
Arbeiten herunter (dann `overwrite=True`, sonst schattet eine veraltete lokale Kopie
den frischen Remote-Stand), oder kann es lokale, noch nicht hochgeladene Änderungen
geben (dann ist der neue Default richtig)?

Als Referenz zeigt das Beispiel-Paket den Worker-Fall:
`csv_profiler/tasks/computation_tasks.py` lädt jetzt mit `Job(job_id, overwrite=True)`.

---

## Kann angefasst werden (Vereinfachung, keine Regression)

### 4. `cosmopolitan_app/logger.py` — der Shim kann weg

Alle drei Builder nehmen jetzt `excluded_packages`, **additiv** zu
`DEFAULT_EXCLUDED_PACKAGES` (`watchdog`, `selenium`):

```python
from cosmo_suite.logger import get_logger_config_web
DOMAIN_EXCLUDED_PACKAGES = ("matplotlib", "PIL", "rasterio")
dictConfig(get_logger_config_web(DEBUG, DOMAIN_EXCLUDED_PACKAGES))
```

Damit entfallen `ExcludeDomainSubmodulesFilter` und `_with_domain_filter` — die
Datei schrumpft auf drei Aufrufe oder verschwindet ganz. `ExcludeSubmodulesFilter`
nimmt das Argument auch direkt (`ExcludeSubmodulesFilter(excluded_packages=…)`).

### 5. `WEB_WORK_DIR` ist im Framework jetzt absolut

`cosmo_suite/config.py` löst den Wert mit `os.path.abspath()` auf. Hier ist nichts
zu tun; nur prüfen, dass `cosmopolitan_app/config.py` den Wert nicht ein zweites Mal
auflöst oder relativ überschreibt.

Grund: Flask löst relative Pfade in `send_from_directory` gegen `app.root_path` auf
(= das App-Paket), nicht gegen das CWD — jedes Job-Bild 404t, ohne Importfehler und
ohne Testfehlschlag.

### 6. Neu, ohne Handlungsbedarf

- **`Job(job_id=…, overwrite=True)`** und `Job.load(overwrite=…)` reichen den Schalter
  aus Punkt 3 durch. Relevant erst, wenn diese App den Framework-`Job` adoptiert.
- **`app_layout(with_reset=False)`**: das Reset-Modal ist Opt-in, die zugehörigen
  Callbacks registrieren sich nur mit `with_reset=True`. Diese App nutzt ihr eigenes
  `cosmopolitan_app/layouts.py` — kein Handlungsbedarf.
- **`page_container_column_layout(content, main_content_id, wrapper_class=None)`**:
  optionaler äußerer Container mit Marker-Klasse. Ohne das Argument ist das DOM
  unverändert.
- **Timeouts:** jeder rclone-Aufruf hat jetzt eine Obergrenze
  (`TRANSFER_TIMEOUT = 600 s` für copy/sync/purge, `CONTROL_TIMEOUT = 60 s` für
  Listings/Delete/Config), und `get_files`/`save_files` prüfen vorab die
  Erreichbarkeit des Remotes (`rclone lsd remote:`, 5 s). Ein Timeout wird **nicht**
  wiederholt. Der Precheck braucht dieselbe Berechtigung, die `create_bucket()` beim
  App-Start ohnehin schon benutzt.

---

## Beim Re-Pin

```toml
"cosmo-suite @ git+https://codebase.helmholtz.cloud/.../cosmo-suite@v0.4.0"
```

Danach `uv lock`, und die Punkte 1–3 abarbeiten, **bevor** die Suite läuft — Punkt 1
und 2 fallen sonst nicht auf.

Neu im Framework-`README.md`, Abschnitt „Consuming the framework": die beiden
Stolpersteine, über die beide Apps gefallen sind —
`[tool.hatch.metadata] allow-direct-references = true` und `git` im CI-Image.
