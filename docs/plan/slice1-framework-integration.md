# Slice 1 — COSMOPOLITAN auf `cosmo_suite` (Tag 2–5)

**Repo:** `cosmopolitan` · **Branch:** `cosmo-suite-integration` (existiert, liegt auf `57c5ad5`)
**Framework-Pin:** `cosmo-suite@v0.3.0` · **Erstellt:** 2026-08-05

---

## 0. Ziel in drei Sätzen

Fig. 2b des SoftwareX-Drafts behauptet, diese App teile ein wiederverwendbares
Framework mit COSMONAUT. Gemessen am 2026-08-05: **null Importe** von `cosmo_suite`.
Dieser Slice ersetzt ~2.700 Zeilen duplizierte Infrastruktur durch Importe — **ohne eine
einzige Domänendatei anzufassen**.

Läuft parallel zum cosmonaut-Agenten gegen den **eingefrorenen** Tag `v0.3.0`. Brauchst
du eine Framework-Änderung: eigener MR im Framework-Repo, neuer Tag, beide Apps
re-pinnen. Nicht selbst am Framework editieren.

---

## 1. Vorbedingung: Reset (muss zuerst, ist noch offen)

Der Branch `cosmo-suite-integration` existiert, aber der Arbeitsbaum trägt weiterhin die
verworfene Universalization-Arbeit: **17 modifizierte Dateien** plus `cosmopolitan_app/
domain.py` und `docs/knowledge/concepts/domain-boundary.md`. Nur
`test/test_domain_boundary.py` ist bereits gelöscht.

Diese Arbeit ist bewusst verworfen: Sie neutralisiert CRNS-Vokabular in UI-Prosa. Der
Paper-Draft verlangt das nirgends — er sagt durchgehend das Gegenteil ("demonstrated
for", "Although demonstrated for CRNS, … transferable"). Der einzige Satz, der Druck
erzeugte, war ein erfundenes Feature ("integrated editor") und ist aus dem Draft
gestrichen.

**Ein echter Fix ist zu retten, bevor der Rest weggeht:**

1. In `cosmopolitan_app/doc_generator.py` steckt ein Bugfix: der
   `# Notes`-Abschnitt der Page-Docstrings leakte nach `assets/docs/documentation.md`,
   entgegen der Zusage im Docstring selbst (Funktion `clean_docstring`). Diesen Teil des
   Diffs isolieren und **als eigenen Commit** sichern.
2. Danach alles andere verwerfen:
   ```bash
   git checkout -- CLAUDE.md cosmopolitan_app/ docs/
   rm -f cosmopolitan_app/domain.py docs/knowledge/concepts/domain-boundary.md
   ```
   `docs/plan/` ist untracked und darf bleiben (enthält dieses Dokument).
3. `./run_pytest.sh` — Baseline festhalten. Erwartung: **22/22 grün**. Falls 17/22:
   die fünf Fehlenden sind e2e-Tests ohne Server, weil Port 8080 belegt ist. Kein
   inhaltlicher Fehlschlag, aber dann ist die Baseline unbrauchbar — Port freimachen und
   wiederholen.

**Nebeneffekt gratis:** Nach dem Reset ist die Doku wieder konsistent. Momentan sagt
`documentation.md` "Point Measurements", während die Screenshots "CRNS Measurements"
zeigen.

**Bewusste Asymmetrie, nicht „symmetrisieren":** In cosmonaut *bleibt* eine
Dokumentationsänderung erhalten (der Abschnitt „Where COSMONAUT Fits", der die App im
Sparse-to-Spatial-Workflow positioniert). Das ist *Positionierung*, die das Paper
braucht. Hier ging es um *Vokabular-Neutralisierung*, die es nicht braucht. Nicht
angleichen.

---

## 2. Der Slice, in Risiko-Reihenfolge

Diff-Zeilen sind gemessen (2026-08-05, Import-Präfixe normalisiert: `cosmo_suite` ↔
`cosmopolitan_app`). „0" heißt identisch bis auf das Präfix.

| # | Modul | FW LOC | Diff | Anmerkung |
|---|---|---|---|---|
| 1 | `logs_table.py` | 74 | **0** | geschenkt — löschen, Importe umbiegen |
| 2 | `object_storage_manager.py` | 396 | **0** | dito; `ObjectStorageError` liegt in beiden Bäumen im selben Modul → nichts zu tun |
| 3 | `files_route.py` | 86 | 2 | Framework setzt `id=DOWNLOAD_BUTTON_SHARED_ID` am Button; Konstante existiert hier nicht |
| 4 | `config.py` | 70 | 21 | Framework-Basis + Domänen-Extras, §3 |
| 5 | `logger.py` | 288 | 7 | Excluded-Liste als Parameter + Typo-Fix, §4.1 |
| 6 | `celery_app.py` / `celery_config.py` | 30 / 114 | 23 / 25 | Task-Manifest bleibt lokal, §4.2 |
| 7 | `pages/logs.py` | 494 | 22 | |
| 8 | `pages/job_management.py` | 207 | 57 | Abweichungen prüfen, nicht blind übernehmen |
| 9 | `pages/worker_management.py` | 874 | 86 | ID-Renames, §4.3 |
| 10 | `pydantic_models.py` → `BaseJobConfig` | 69 | — | chirurgisch, §4.4 |

**Nach jedem Schritt:** `./run_pytest.sh` und App starten. Nicht mehrere Schritte
bündeln — bei 874-Zeilen-Seiten willst du wissen, welcher Schritt es war.

**Erster Schritt vor allem anderen** — Pin setzen:

```toml
# pyproject.toml → [project].dependencies
"cosmo-suite @ git+https://codebase.helmholtz.cloud/ufz/tb5-smm/met/wg7/cosmo-suite@v0.3.0",
```
Dann `uv lock`. Referenz für den Dev-Loop mit lokalem Framework-Baum:
`../cosmo-suite/examples/csv_profiler/pyproject.toml` (`[tool.uv.sources]` mit
`editable = true`).

---

## 3. `config.py` — Basis plus Extras

Verifiziert: die Env-Var-**Namen** stimmen exakt überein. Kein Rename nötig (anders als
in cosmonaut). Das Framework exportiert bereits die abgeleiteten Namen `PORT`
(aus `FLASK_PORT`) und `DEBUG` (aus `FLASK_DEBUG`), dazu alle `POSTGRES_*`, `REDIS_*`,
`OBJECT_STORAGE_*`, `WEB_*` und `JOB_WORK_DIR_TEMPLATE`.

Diese Variablen liest das Framework **nicht** — sie bleiben hier:
`TILESERVER_URL`, `EMAIL_SERVER`, `EMAIL_PORT`, `EMAIL_USERNAME`, `EMAIL_PASSWORD`,
`EMAIL_SENDER`, `MAINTAINER_EMAIL`.

```python
from cosmo_suite.config import getenv

TILESERVER_URL = getenv("TILESERVER_URL")
# … die übrigen sechs
```

**Die eine echte Verhaltensänderung:** Das Framework macht
`load_dotenv(find_dotenv(usecwd=True))` statt `load_dotenv()` — es sucht die `.env` ab
dem **CWD des laufenden Prozesses**, nicht neben `config.py` (das liegt jetzt in
site-packages). Der Prozess muss also aus dem Repo-Root starten. **Zu prüfen:**
`working_dir` in allen `docker-compose*.yml`, `dev_up.sh`, `run_pytest.sh`, und die
Deployment-Manifeste.

---

## 4. Vorgemessene Stolperstellen

### 4.1 `logger.py`
- Cosmopolitan filtert zusätzlich `"matplotlib"`, `"PIL"`, `"rasterio"` aus den Logs. Die
  Excluded-Liste muss als **Parameter** reingehen, nicht im Framework hartkodiert werden.
- **Typo-Falle:** hier heißt die Funktion `get_logger_config_compuation` (fehlendes `t`),
  im Framework `get_logger_config_computation`. Alle Call-Sites anpassen.
- Framework-Symbole: `PostgreSQLHandler`, `ExcludeSubmodulesFilter`,
  `get_logger_config_computation`, `get_logger_config_web`, `get_logger_config_worker`.

### 4.2 Celery
`BaseCeleryConfig` subclassen, eigene `task_routes`/`beat_schedule` setzen. `celery_app.py`
bleibt lokal als Task-Manifest. **Wichtig:** `NAME_CLEANUP_TASK`/`NAME_TEST_TASK` zeigen
im Framework auf `cosmo_suite.tasks.*` — die Routes entsprechend umstellen, sonst landen
Cleanup- und Test-Tasks in **keiner** Queue.

### 4.3 HTML-IDs
42 gemeinsame Konstanten haben **identische Namen und Werte** — inklusive
`ERROR_MODAL_SHARED_ID`, `LOADING_OVERLAY_MODAL_SHARED_ID`, alle `*_LOGS_ID` und
`*_JOB_MANAGEMENT_ID`. Diese sechs heißen hier anders:

| Framework | hier (`constants/html_ids.py`) |
|---|---|
| `WORKER_REFRESH_BTN_WORKER_MANAGEMENT_ID` | `REFRESH_BUTTON_WORKER_MANAGEMENT_ID:169` |
| `WORKER_KILL_BTN_WORKER_MANAGEMENT_ID` | `KILL_BUTTON_WORKER_MANAGEMENT_ID:171` |
| `WORKER_CANCEL_BTN_WORKER_MANAGEMENT_ID` | `CANCEL_BUTTON_WORKER_MANAGEMENT_ID:172` |
| `WORKER_MANAGEMENT_DUMMY_COMPONENT_…_ID` | `DUMMY_DIV_WORKER_MANAGEMENT_ID:187` |
| `WORKER_STATS_CARD_DIV_…_ID` | `STATS_CARD_DIV_WORKER_MANAGEMENT_ID:188` |
| `WORKER_LAST_REFRESH_DIV_…_ID` | `LAST_REFRESH_DIV_WORKER_MANAGEMENT_ID:189` |

Sobald die Framework-Seite übernommen ist, kommen die IDs aus dem Framework und die
lokalen Definitionen fallen weg. **Die Werte ändern sich dabei**
(`refresh-button-…` → `worker-refresh-btn-…`) → **Playwright-Locators in `test/`
nachziehen.** Prüfe auch `KILL_MODAL_CANCEL_BUTTON_…:173` und
`CANCEL_MODAL_CANCEL_BUTTON_…:179` auf Gegenstücke.

### 4.4 `pydantic_models.py`
Das Framework liefert `validate_job_id` (identisches Regelwerk: 8–50 Zeichen, `^\w+$`)
und `BaseJobConfig` mit genau zwei Feldern (`job_id`, `upload_file_name`) plus
`model_config = ConfigDict(validate_assignment=True)`.

→ `ModelWebsite(BaseJobConfig)`, lokales `job_id`-Feld und lokales `validate_job_id`
löschen. **`validate_assignment=True` nicht abschalten** — das ist ein
Sicherheitsfeature (kein Modell kann eine ungültige `job_id` per Zuweisung bekommen).

Die 19 Felder aus `soil_moisture_prediction.InputParameters` und die 9 hier deklarierten
(`crns_upload`, `train_data`, `station_data`, `rover_data`, `pred_streams`,
`predictor_upload`, `date_range`, `email`, `job_id`) bleiben unberührt — bis auf `job_id`,
das nach oben wandert.

### 4.5 `dotenv`-Kollision
`pyproject.toml:17` pinnt `"dotenv>=0.9.9,<0.10"` — das **Fremdpaket**. Das Framework
pinnt `python-dotenv>=1,<2`. Beide liefern das Modul `dotenv`. Beim ersten `uv sync`
prüfen, welches gewinnt. **Empfehlung: auf `python-dotenv` wechseln und `dotenv`
streichen.**

### 4.6 Assets kommen nicht aus dem Wheel
Das Framework-Wheel enthält **kein** `assets/` und kein `static/` (siehe
`[tool.hatch.build.targets.wheel] packages = ["cosmo_suite"]`). Icon-Pfade und
`external_stylesheets` bleiben app-seitig. Das Framework erwartet
`/static/icon_navbar.svg`, hier liegt `/static/icon_white.svg`. Und: das Beispiel lädt
Bootstrap-Icons per CDN (`dbc.icons.BOOTSTRAP`), diese App übergibt kein
`external_stylesheets` — **prüfen, dass `bi bi-*`-Icons in Framework-Komponenten nicht
leer rendern.**

### 4.7 Port 8080 / `run_pytest.sh`
`run_pytest.sh:152` macht `source .env` — und zwar **nach** `cp env_test_local .env`. Ein
`FLASK_PORT=8090 ./run_pytest.sh` wird dadurch überschrieben; ein anderer Port geht nur
über eine getrackte Datei. Cosmonauts Suite nutzt denselben Port 8080, **die beiden
Suites können nicht parallel laufen.** Mit dem cosmonaut-Agenten abstimmen oder
serialisieren.

Nie `pytest` direkt aufrufen — nur `./run_pytest.sh`.

### 4.8 `Job.app_version` — neuer vierter Seam (erst relevant mit dem Framework-`Job`)

Neu in `cosmo-suite@v0.3.0`: der Framework-`Job` hat einen vierten, **optionalen**
Seam neben `config_model`/`file_validator`/`submit_handler`:

```python
Job.app_version = smp_version   # in app.py UND celery_app.py
```

Er landet in der `version`-Spalte jedes Jobs. Default ist die Framework-Version
(jetzt aus der Distribution-Metadata, nicht mehr hartkodiert).

In diesem Slice **nichts zu tun** — `job.py` bleibt draußen (§5), diese App benutzt
ihren eigenen `Job`. Wichtig für den Zeitpunkt, an dem er übernommen wird: hier wird
`self.version = smp_version` gestempelt (`job.py:264` und `:291`), also die Version
des Rechenmoduls, nicht der App. Ohne gesetzten Seam ersetzt die Framework-Version
diese Provenance **still** — kein Fehler, nur falsche Herkunft in allen neuen Jobs.
Und: den Seam in `celery_app.py` mitsetzen, nicht nur in `app.py`.

---

## 5. Ausdrücklich NICHT in diesem Slice

Die Zahlen sagen warum — das ist Domänenverflechtung, kein liegengelassenes Aufräumen:

| Modul | Diff | Grund |
|---|---|---|
| `postgres_manager.py` | 894 | Ab `_extract_date:416` ~700 Zeilen reine CRNS/TimeIO-Domäne. Die ersten 18 Symbole decken sich, aber `JobTable` hat hier zusätzlich `prepared_input`, und sieben eigene Tabellen müssten auf die Framework-`Base` umgehängt werden. Slice 2. |
| `layouts.py` | 250 | Navbar/Branding domänenspezifisch; Framework-`app_layout()` bringt ein Reset-Confirm-Modal mit, das diese App nicht hat. |
| `job.py` | 637 | 802 vs. 355 Zeilen, Löwenanteil CRNS (`preview_area`, `prepare_input_files`, `_write_crns`, Projektionen). Der Framework-`Job` ist noch ein konkreter `Job`, kein `BaseJob`-Contract. |
| `error_handling.py` | 93 | Braucht erst den `on_unhandled`-Hook im Framework: `handle_error:253` mailt an `MAINTAINER_EMAIL`, das Framework loggt nur. Fehlt der Hook, gehen Maintainer-Mails **still** verloren. Dazu kollidiert `FileValidationError` (Framework definiert eine eigene, hier kommt sie aus `soil_moisture_prediction.input_file_parser`). |

Ebenfalls draußen: `doc_generator`, `email_service`, `form_template_factory`, `map_utils`,
`screenshot_generator`, `timeio_*`, `utils` — reine Domäne.

---

## 6. Definition of Done

- `pyproject.toml` pinnt `cosmo-suite@v0.3.0`, `uv.lock` aktualisiert.
- Die zehn Punkte aus §2 erledigt; die ersetzten lokalen Module **gelöscht**, nicht
  danebenliegend.
- `./run_pytest.sh` grün, mindestens auf Baseline-Niveau (22/22).
- Manuell durchgeklickt: Upload → Submit → Results → Logs → Job-Management →
  Worker-Management. Insbesondere Worker-Management (ID-Werte geändert) und Download
  (`files_route`).
- **Gemessene** Zahl gelöschter Zeilen berichten (`git diff --stat` gegen den
  Reset-Commit) — die geht als Belegzahl ins Paper.
- `ruff check` und `ruff format --check` sauber.

---

## 7. Konventionen

`CLAUDE.md` und `docs/conventions/*` gelten: keine `dict.get()`, kein bare
`except Exception`, keine Inline-Imports, HTML-IDs nur aus Konstanten, kein Inline-CSS.

Zwei Dash-Fallen, die hier teuer gelernt wurden (`docs/knowledge/concepts/dynamic-forms.md`):
1. **Callbacks werden zur Importzeit verdrahtet.** Fehlt ein referenziertes Feld im DOM,
   kann Dash den Callback nicht auflösen und das **gesamte** Formular validiert nicht mehr.
   Bedingte Felder *verstecken*, nicht weglassen.
2. **React-Fehler #31:** `FormFactory.process_layout` ersetzt ein `InputField` durch eine
   Liste; mehrere in einem Container ergeben verschachtelte Listen → Container
   verschwindet lautlos. Ein Wrapper-`Div` pro `InputField`.
