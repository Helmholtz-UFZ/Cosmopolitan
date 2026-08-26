# Slice 1b — COSMOPOLITAN holt die drei Framework-Seiten nach

**Repo:** `cosmopolitan` · **Branch:** `cosmo-suite-integration-2` (Fortsetzung, HEAD `b180288`)
**Framework-Pin:** bleibt zunächst `v0.3.0` · **Erstellt:** 2026-08-06

---

## 0. Warum das nachkommt

Slice 1 hat hier **−842 Zeilen** netto gebracht, in COSMONAUT **−1834**. Die Lücke ist
fast vollständig eine Sache: die drei Framework-Seiten und der `background_job_manager`
sind hier liegengeblieben, in COSMONAUT nicht.

| Modul | hier lokal | COSMONAUT |
|---|---|---|
| `pages/worker_management.py` | **866 Z.** | 871 → 47 |
| `pages/logs.py` | **490 Z.** | 511 → 34 |
| `pages/job_management.py` | **212 Z.** | (eigene Seite, n/a) |
| `background_job_manager.py` | **265 Z.** | 284 → 111 |

**Die Entscheidung, in Slice 1 zu stoppen, war richtig.** Der Grund — die Framework-Seiten
ziehen `cosmo_suite.db_manager`, `cosmo_suite.layouts` und
`cosmo_suite.background_job_manager` mit in den Prozess — stand nicht im Plan und ist
echt. Er wurde korrekt erkannt.

Inzwischen ist die Frage aber beantwortet, und zwar empirisch: **COSMONAUT ist diesen Weg
gegangen und hat ihn am laufenden System verifiziert.** Zwei Engines gegen dieselbe
Postgres, zwei `Base`-Registries — funktioniert, weil der Framework-`DbManager` dort nur
Log-Queries bedient. Diese App kommt in dieselbe Lage, mit derselben Begrenzung.

Das ist ein **bewusster Übergangszustand**, den Slice 2 auflöst (Tabellen auf die
Framework-`Base`). Er wird hier dokumentiert, nicht versteckt.

**Ziel:** ~1.350 weitere Zeilen geteilt statt dupliziert, und die beiden Apps werden
symmetrisch — Fig. 2b des Papers zeigt sie symmetrisch.

---

## 1. Schritt 0: pushen

`cosmo-suite-integration-2` liegt mit 8 Commits nur lokal. Vor allem Weiteren pushen.
Ein lokaler Branch mit einer Woche Arbeit ist ein unnötiges Risiko.

---

## 2. Reihenfolge

COSMONAUTs Rezept ist erprobt; es lohnt sich, dort nachzusehen statt neu zu erfinden.
Referenz-Commits in `../ufz-cosmonaut`: `b95bf50` (Celery + BackgroundJobManager),
`7f2ff7e` (die beiden Seiten), `bab89a9` (Layout-Korrektur).

### 2.1 `background_job_manager.py` zuerst (265 → ~110)

Muss vor den Seiten kommen: `cosmo_suite/pages/worker_management.py:48` importiert
`cosmo_suite.background_job_manager.background_job_manager`. Ohne diesen Schritt laufen
zwei Manager mit zwei Celery-Clients im Prozess.

Framework-Basis erben, domänenseitig bleiben: `NAME_COMPUTATION_TASK`,
`NAME_UPDATE_DB_TASK`, `submit_computation_job(job)`, `submit_update_db_task()` — als
dünne Wrapper um `submit_named_job`. Das Modul-Level-`__getattr__`-Muster (lazy
Singleton) ist in beiden Bäumen gleich, also kompatibel.

**Dabei den vorbestehenden Bug mitnehmen** (§4).

### 2.2 Die drei Seiten (1.568 → ~120 als Shims)

`pages/logs.py`, `pages/job_management.py`, `pages/worker_management.py` werden zu Shims
über `cosmo_suite.pages.*` — genau wie COSMONAUTs `pages/logs.py` (34 Z.) und
`pages/worker_management.py` (47 Z.).

Einzeln machen, nach jeder Seite `./run_pytest.sh` **und** App starten. Bei
866-Zeilen-Seiten willst du wissen, welche es war.

**`pages/job_management.py` gesondert prüfen.** COSMONAUT hat sein Pendant
(`pages/job_manager.py`, 411 Diff-Zeilen) bewusst **nicht** übernommen — dort ist es eine
andere Seite. Hier wurde in Slice 1 ein Diff von 57 Zeilen gemessen, also eine echte
Variante. Trotzdem: erst lesen, was die 57 Zeilen sind, dann entscheiden. Wenn eine
Domänenspalte oder eine Aktion dranhängt, bleibt die Seite lokal — 212 Zeilen sind kein
Grund, Funktionalität zu verlieren.

### 2.3 HTML-IDs nachziehen

Sechs Konstanten heißen hier anders, und **die Werte ändern sich mit**
(`refresh-button-…` → `worker-refresh-btn-…`):

| Framework | hier (`constants/html_ids.py`) |
|---|---|
| `WORKER_REFRESH_BTN_WORKER_MANAGEMENT_ID` | `REFRESH_BUTTON_…:169` |
| `WORKER_KILL_BTN_WORKER_MANAGEMENT_ID` | `KILL_BUTTON_…:171` |
| `WORKER_CANCEL_BTN_WORKER_MANAGEMENT_ID` | `CANCEL_BUTTON_…:172` |
| `WORKER_MANAGEMENT_DUMMY_COMPONENT_…_ID` | `DUMMY_DIV_…:187` |
| `WORKER_STATS_CARD_DIV_…_ID` | `STATS_CARD_DIV_…:188` |
| `WORKER_LAST_REFRESH_DIV_…_ID` | `LAST_REFRESH_DIV_…:189` |

→ **Playwright-Locators in `test/` nachziehen.** COSMONAUT hat seine Locators direkt aus
`cosmo_suite.constants` gezogen, statt sie zu duplizieren — übernehmen. Die dort neu
formulierte Regel gilt symmetrisch: **wer die Komponente rendert, besitzt ihre ID.**
Danach die lokal ungenutzt gewordenen Konstanten löschen (COSMONAUT: 34 Stück).

### 2.4 `files_route.py` (84 Z.) — prüfen, wahrscheinlich lassen

War Schritt 3 in Slice 1 und wurde in **beiden** Apps übersprungen. Dem Framework fehlt
ein Gegenstück zu COSMONAUTs `/download/<job_id>/route.gpx`. Ob diese App eine
domänenspezifische Route braucht: nachsehen. Wenn nein, ist es ein billiger Punkt; wenn
ja, bleibt es lokal und geht als Anforderung in Slice 2 (registrierbarer
Domänen-Dateipfad).

---

## 3. Der Zwei-Engine-Zustand: dokumentieren, nicht verstecken

Nach diesem Slice laufen im Prozess:
- `cosmopolitan_app/postgres_manager.py` — eigene `create_engine`/`sessionmaker`/`Base`
- `cosmo_suite/db_manager.py:98` — dieselben, für die Log-Queries der Framework-Seite

Beide gegen dieselbe Postgres, beide mit einer `LogTable`→`logs`- und
`JobTable`→`jobs`-Zuordnung in getrennten Registries.

**Zu tun:**
1. Verifizieren, dass das lokale `logs`-Schema zur Framework-`LogTable` passt — sonst
   rendert die Log-Seite leer oder wirft beim Mapping. COSMONAUT hat das mit echten
   Records geprüft (42 Level-Badges).
2. `Base.metadata.create_all()` darf **nicht** auf beiden Registries laufen. Prüfen, wo
   das aufgerufen wird (Test-Setup, `init.sql`-Pfad).
3. Einen Decision Record in `docs/knowledge/` anlegen: warum zwei Engines akzeptiert
   wurden, was das begrenzt, und dass Slice 2 es auflöst.

---

## 4. Der vorbestehende Queue-Bug (mitnehmen)

`background_job_manager.py:144` sendet die Test-Task nach `queue="test"`, der Worker
konsumiert aber `default,computation,maintenance`. Die Task bleibt für immer PENDING —
im Redis bestätigt. COSMONAUTs Worker konsumiert `test`, hier fehlt die Queue.

Nicht von dieser Arbeit verursacht, aber `background_job_manager.py` wird in §2.1
ohnehin angefasst, und im Framework zeigt `NAME_TEST_TASK` jetzt auf
`cosmo_suite.tasks.test_tasks` — also ist das genau der richtige Moment.

**Fix:** entweder `test` in die Queue-Liste des Workers aufnehmen (symmetrisch zu
COSMONAUT) oder die Test-Task nach `default` routen. Erste Variante bevorzugen — sie
gleicht die Asymmetrie zwischen den Apps an, und genau solche Drift soll das Framework
beseitigen. Vorher die Stelle finden, an der die Queue-Liste des Workers definiert ist
(nicht in `docker-compose*.yml` oder `docker/*.sh` gefunden — vermutlich Startskript oder
k8s-Manifest).

---

## 5. Wissen ablegen

Neue Datei `docs/conventions/framework_integration.md` (die Memory-Policy in `CLAUDE.md`
verlangt eine bewusste Ablage — eine neue, fokussierte Datei ist ausdrücklich erlaubt):

- **CWD-Regel:** Das Framework lädt `.env` mit `find_dotenv(usecwd=True)`; jeder
  Entrypoint muss aus dem Repo-Root starten.
- **Freeze-Regel:** App-Agenten arbeiten gegen einen festen Framework-Tag. Braucht man
  eine Änderung, ist das ein MR im Framework mit neuem Tag — kein lokaler Patch am
  installierten Paket.
- **Adoptionsregel** (von COSMONAUT formuliert, gilt symmetrisch): Übernimm nur, wo die
  Framework-Version verhaltensgleich oder besser ist. Sonst bleibt das lokale Modul, die
  Abweichung wird **in dessen Docstring benannt**, und es entsteht ein Framework-MR.
  Diff-Größe sagt *nicht* vorher, welcher Fall vorliegt — lesen, nicht zählen.
- **ID-Besitz:** Wer die Komponente rendert, besitzt ihre ID.
- **`[tool.hatch.metadata] allow-direct-references = true`** und `git` im CI-Image.

`docs/plan/slice1-execution-notes.md` ist untracked und darf es bleiben — der bleibende
Teil gehört in die Konventionsdatei.

---

## 6. Nach `v0.4.0`

Der Framework-Batch 2 (`../cosmo-suite/docs/plan/slice1b-framework-batch2.md`) läuft
**parallel** zu diesem Slice. Er berührt nichts, was hier gebraucht wird — arbeite gegen
`v0.3.0` weiter und pinne erst am Ende um.

**Diese App endet ebenfalls auf `v0.4.0`** — `v0.3.0` ist nur der Arbeits-Pin, damit du
nicht auf Batch 2 warten musst. Das Umpinnen ist ein **geplanter Schritt mit vier
benannten Deltas**, kein Nachgedanke:

1. **`get_files`-Default kippt** — der schärfste Punkt. Diese App hat ihren lokalen
   `object_storage_manager` in Slice 1 komplett gelöscht und ruft die Framework-Funktion
   direkt: `job.py:249` → `get_files(self.job_id)`. Heute überschreibt das
   bedingungslos; `v0.4.0` setzt den Default auf `overwrite=False`
   (`--ignore-existing`), weil COSMONAUT sonst ungesyncte Street-Edits verliert.
   **Für diese App ist das eine stille Verhaltensänderung.** Entscheide bewusst: setze
   an `job.py:249` explizit `overwrite=True`, oder bestätige, dass der neue Default hier
   richtig ist. Nicht durchrutschen lassen — `save_files` in `:646` mit ansehen.
2. **`BaseJobConfig` wird aufgespalten.** `pydantic_models.py:32` ist
   `class ModelWebsite(InputParameters, BaseJobConfig)`, und der Docstring benennt, dass
   `BaseJobConfig` das generische `upload_file_name`-Feld beisteuert. Nach der
   Aufspaltung heißt die Basis mit diesem Feld **`UploadJobConfig`** — dorthin wechseln,
   sonst fällt das Feld weg.
3. **`BaseCeleryConfig.task_time_limit` wird `None`.** Diese App hat die
   65-Minuten-Grenze bisher stillschweigend geerbt. **Rückmeldung an Agent A nötig:**
   Soll COSMOPOLITAN ein Limit behalten? Dann künftig explizit in der eigenen
   `CeleryConfig` setzen. Sonst fällt hier unbemerkt ein Schutz weg. (Random-Forest-
   Regionalisierung skaliert anders als COSMONAUTs O(n²)-Routing — ein Limit ist hier
   plausibel sinnvoll.)
4. **`logger` bekommt `excluded_packages`** — danach kann der lokale Shim (`logger.py`,
   51 Z. mit `matplotlib`/`PIL`/`rasterio`) verschwinden.

Punkte 1–3 sind **Rückfragen an Agent A, bevor der mergt**, nicht Arbeit, die du danach
allein aufräumst. Batch 2 ist für diese App nicht neutral.

**Nicht betroffen, geprüft:** Die `WEB_WORK_DIR`-`abspath`-Änderung aus Batch 2 trifft
diese App nicht. `files_route.py:48` benutzt einen fest verdrahteten relativen Pfad
(`work_dir/{job_id}`) statt `WEB_WORK_DIR`, mit Kommentar an `:45`. COSMONAUTs
404-Falle existiert hier nicht.

---

## 7. Definition of Done

- Branch gepusht (Schritt 0, **zuerst**).
- `background_job_manager` auf Framework-Basis; die drei Seiten als Shims oder mit
  begründeter Ausnahme für `job_management`.
- ID-Renames durch, Playwright-Locators aus `cosmo_suite.constants`, ungenutzte
  Konstanten gelöscht.
- `./run_pytest.sh` grün (Baseline **20**, nicht 22 — die zwei fehlenden waren die
  verworfenen `test_domain_boundary`-Tests, keine Regression).
- Am **laufenden** System durchgeklickt: Logs, Job Management, Worker Management. Konkret
  prüfen: Log-Records rendern echt (nicht leer), Worker wird erkannt, Kill/Cancel-Buttons
  reagieren, Test-Task landet **nicht** mehr dauerhaft in PENDING.
- Zwei-Engine-Entscheidung als Decision Record in `docs/knowledge/`.
- `docs/conventions/framework_integration.md` angelegt.
- **Gemessene** Zeilenzahl berichten (`git diff --stat 1ff2a08 HEAD -- cosmopolitan_app/`)
  — die kumulierte Zahl geht als Belegzahl ins Paper.
- `ruff check` **und** `ruff format --check` sauber (hier ist beides schon sauber — das
  bitte so halten).

---

## 8. Konventionen

`CLAUDE.md` und `docs/conventions/*`. Die zwei Dash-Fallen aus
`docs/knowledge/concepts/dynamic-forms.md` gelten weiter: Callbacks werden zur Importzeit
verdrahtet (bedingte Felder *verstecken*, nicht weglassen), und React-Fehler #31 durch
verschachtelte Listen (ein Wrapper-`Div` pro `InputField`).

**Port 8080:** COSMONAUTs Suite bindet denselben Port. Die restlichen Test-Services liegen
auf eigenen Ports (5433/9010/6380), es kollidiert also nur Dash. Eine Kollision sieht wie
**Setup-ERRORs** aus, nicht wie Failures — nicht als inhaltlichen Fehlschlag fehldeuten.
Mit dem cosmonaut-Agenten serialisieren.
