# Slice 1 — Ausführungsnotizen (2026-08-06)

Ergänzung zu `slice1-framework-integration.md`. Gemessen während der Ausführung auf
`cosmo-suite-integration-2`, Basis-Commit `1ff2a08`, Framework-Pin `v0.3.0` (`0681cd1`).

## Abweichungen zum Plan (gemessen, nicht geschätzt)

### 1. Baseline ist 20, nicht 22

`./run_pytest.sh` sammelt auf diesem Branch **20 Tests**, alle grün (146 s). Die im Plan
genannten 22 stammen von einem älteren Stand.

### 2. Der Arbeitsbaum war beim Start bereits sauber

§1 („17 modifizierte Dateien verwerfen") war gegenstandslos — der Reset hatte schon
stattgefunden. Die verworfene Universalization-Arbeit liegt vollständig in `dac4f50`
auf Branch `cosmo-suite-integration`. Der zu rettende `clean_docstring`-Fix wurde von
dort isoliert übernommen (Commit `8b2aff3`); die Vokabular-Neutralisierung nicht.

### 3. Der Plan misst Text-Diffs, nicht den Importgraphen des Frameworks

Das ist die wichtigste Abweichung. Vier der zehn Schritte aus §2 hängen an Modulen, die
§5 **ausdrücklich aus Slice 1 heraushält**:

| Schritt | Framework-Modul importiert | in §5 ausgeschlossen? |
|---|---|---|
| 3 `files_route.py` | `cosmo_suite.job.Job` | ja (`job.py`, 637 Diff) |
| 7 `pages/logs.py` | `cosmo_suite.db_manager`, `cosmo_suite.layouts` | ja (894 / 250 Diff) |
| 8 `pages/job_management.py` | `cosmo_suite.job`, `db_manager`, `layouts` | ja |
| 9 `pages/worker_management.py` | `cosmo_suite.background_job_manager`, `layouts` | teilweise |

Konkret bedeutet „Framework-Seite übernehmen" hier: **zwei parallele Infrastruktur-Stacks
in einem Prozess** — zwei SQLAlchemy-Engines/Pools auf dieselbe DB, zwei Celery-Clients,
zwei `Job`-Klassen. Kein Importfehler, aber auch keine saubere Grenze.

Zwei Einzelheiten dazu:

- **`worker_management` + Test-Task-Button:** Der Framework-`background_job_manager`
  submittet `cosmo_suite.tasks.test_tasks.long_running_test`. Cosmopolitans Worker
  registriert `cosmopolitan_app.tasks.test_tasks.long_running_test`. Der Button auf der
  Seite würde einen Task einreihen, den kein Worker kennt.
- **`job_management` ist gemessen ein Rückschritt**, keine Variante:
  1. Link auf die Submission-Seite ist hartkodiert (`/job-submission/{job_id}`) statt
     über `dash.page_registry["pages.submission"]["path_template"]` aufgelöst — in
     dieser App der falsche Pfad.
  2. Der Loading-Overlay-Callback ist server-seitig. `docs/conventions/callbacks.md`
     schreibt clientside vor, mit begründetem Race als Anlass. Die Framework-Version
     kommentiert das sogar selbst als bekannten Kompromiss.
  3. Der Docstring ist gekürzt — er speist die generierte Nutzerdokumentation.

### 4. `logger.py`: der Parameter-Seam existiert in v0.3.0 nicht

§4.1 verlangt, die Excluded-Liste „als Parameter" zu übergeben.
`cosmo_suite.logger.ExcludeSubmodulesFilter` hat den Parameter nicht — die Liste steht
hart in `filter()`. Unter der Freeze-Regel ist das Framework nicht editierbar, also
bleibt lokal ein ~30-Zeilen-Shim: Subklasse des Filters plus Austausch der Filter-Fabrik
in den zurückgegebenen dictConfig-Dicts. **Kandidat für das nächste Framework-Tag:**
`excluded_packages` als Argument.

### 5. Nicht im Plan gelistete Fundstellen

- `docker/worker.Dockerfile:61` ruft `object_storage_manager.py` **als Skript über den
  Pfad** auf. Nach dem Löschen des lokalen Moduls: `python3 -m
  cosmo_suite.object_storage_manager setup_remote`.
- `pyproject.toml` braucht `[tool.hatch.metadata] allow-direct-references = true`,
  sonst lehnt hatchling den Git-URL-Pin ab. Gilt für COSMONAUT genauso.
- `doc_generator.extract_docstring` liest Page-Dateien **über den Dateipfad**
  (`cosmopolitan_app/pages/<name>.py`). Sobald eine Seite aus dem Framework kommt,
  bricht die Doku-Generierung — muss dann über `importlib` aufgelöst werden.
- `test_env.py` importiert `env_vars` aus `cosmopolitan_app.config`; die Liste ist jetzt
  `framework_env_vars + domain_env_vars` (18 + 7 = 25, unverändert in Summe).

### 6. Geschenkt, aber nicht im Plan

`cosmopolitan_app/tasks/test_tasks.py` ist **byte-identisch** zum Framework (0 Diff).
Freie Löschung; der Task-Name bleibt der lokale, weil er bei der Registrierung in
`celery_app.py` explizit übergeben wird.

## CWD-Annahme der `.env` (§3) — geprüft

`find_dotenv(usecwd=True)` sucht ab dem CWD **aufwärts**. Geprüft:

| Ort | CWD | `.env` vorhanden |
|---|---|---|
| `docker/dev.Dockerfile` | `WORKDIR /python_docker/cosmopolitan` | ja (Bind-Mount) |
| `docker/worker.Dockerfile` | dito | ja (`COPY env_prod .env`) |
| `docker/prod.Dockerfile` | dito | ja (`COPY env_prod .env`) |
| `run_pytest.sh` | Repo-Root | ja (`cp env_test_local .env`) |
| `deployments/ufz/{prod,stage}/values.yaml` | kein `workingDir`-Override | Image-WORKDIR gilt |

Kein Fundort, an dem der Prozess außerhalb des Repo-Roots startet.
