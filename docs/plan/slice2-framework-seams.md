# Slice 2: COSMOPOLITAN auf die neuen Framework-Nahtstellen

**Repo:** `cosmopolitan` · **Branch:** neu, `slice2-framework-seams` off `main`
**Framework-Pin:** `v0.4.1` → **`v0.5.0`** · **Erstellt:** 2026-08-19

---

## 0. Warum, und die Regel für parallele Arbeit

Slice 1 und 1b haben hier 2.313 Zeilen Infrastruktur ins Framework verlagert. Was noch
lokal liegt, war nicht Bequemlichkeit, sondern durch fehlende Nahtstellen blockiert.
`cosmo-suite@v0.5.0` liefert sie jetzt alle.

Läuft parallel zum cosmonaut-Agenten gegen den **eingefrorenen** Tag `v0.5.0`. Brauchst
du eine Framework-Änderung: eigener MR im Framework-Repo, neuer Tag, **beide** Apps
re-pinnen. Nicht selbst am Framework editieren. Das hat in Slice 1 funktioniert und war
der Grund, dass zwei Agenten gleichzeitig arbeiten konnten.

**Zuerst lesen, bevor du eine Framework-Seite oder ein Framework-Modul übernimmst:**
`../cosmo-suite/docs/conventions/framework_page_imports.md`. Es beschreibt drei stille
Fehlschläge, von denen diese App einen schon selbst getroffen hat (§4.1). Dazu
`database_schema.md` als Hintergrund; §2.5 selbst ist vertagt.


> **Nachtrag 2026-08-21, verbindlich.** Zwei Stellen dieses Plans waren falsch, beide
> gemessen und korrigiert: §2.1 (`track_task_name`) und §2.5, das so in **keiner** der
> beiden Apps ausführbar ist. §2.5 ist vertagt, der Rest gilt unverändert. Vor der Arbeit
> auch §0.1 lesen, dort steht die Ursache der gescheiterten Baseline.

### 0.1 Warum die lokale Suite nicht startet, und warum es nicht am Code liegt

Gemessen am 2026-08-21: der UFZ-VPN (Cisco AnyConnect, Interface `cscotun0`) schiebt
Routen in die Tabelle, die die Docker-Bridge-Netze einsammeln:

```
default          dev cscotun0
172.18.0.0/16    dev cscotun0        <- vom VPN
172.18.0.0/16    dev br-<projekt>    <- von Docker
```

`ip route get <container-ip>` löst auf `cscotun0` auf. `docker-proxy` nimmt die
Verbindung auf `localhost` also an und schickt das zweite Bein in den Tunnel, wo es
verschwindet. Belegt an einem unbeteiligten, gesunden Container: von innen erreichbar,
vom Host weder über den veröffentlichten Port noch über die Container-IP.

**Konsequenz:** solange der VPN verbunden ist, ist keine lokale Suite lauffähig, egal in
welchem Repo. VPN trennen. Die Symptome sind Timeouts in `pytest_configure`
(MinIO-Connectivity-Check) oder "server closed the connection unexpectedly", also
Meldungen, die nach einem Framework- oder Pin-Problem aussehen und keines sind.

Zwei Prüfungen, bevor du irgendetwas anderes vermutest:

```bash
ip route get 172.18.0.2          # darf NICHT auf cscotun0 zeigen
docker exec <container> sh -c 'wget -q -O /dev/null -T 3 http://localhost:<port>/'
```

Antwortet der Container von innen und der Host nicht, ist es die Route, nicht der Code.

**Unabhängig davon ein echter Bug:** `pg_isready` ohne `-h 127.0.0.1` prüft den
Unix-Socket, und initdbs temporärer Server antwortet dort schon, während er
`listen_addresses=''` fährt und gar kein TCP anbietet. Der Check meldet dann "ready",
während der Endpunkt der Tests noch tot ist. In `run_pytest.sh` gehört `-h 127.0.0.1`
hin. CI ist nicht betroffen, dort prüft `pg_isready -h postgres` schon über TCP.

---

## 1. Vorbedingung: Pin hochziehen

```toml
# pyproject.toml → [project].dependencies
"cosmo-suite @ git+https://codebase.helmholtz.cloud/ufz/tb5-smm/met/wg7/cosmo-suite@v0.5.0",
```

Dann `uv lock`, Suite laufen lassen, Baseline festhalten (Erwartung **20/20**).
`v0.5.0` ist rein additiv gegenüber `v0.4.1`, es sollte sich also nichts ändern. Tut es
doch, ist das ein Befund und keine Kleinigkeit.

---

## 2. Der Slice, in Risiko-Reihenfolge

Nach jedem Schritt `./run_pytest.sh` **und** App starten. Nicht bündeln.

| # | Modul | lokal | Nahtstelle, die es entsperrt |
|---|---|---|---|
| 1 | `background_job_manager.py` | 106 Z. | `submit_job(task_name, job_id, queue, *, track_task_name=False, **opts)` |
| 2 | `error_handling.py` | 279 Z. | `handle_error(error, *, on_unhandled=...)`, §2.2 |
| 3 | `job.py` | 807 Z. | `BaseJob`, §2.3 |
| 4 | `files_route.py` | 97 Z. | `serve_files(app, *, job_class=...)`, §2.4 |
| 5 | `postgres_manager.py` | 1241 Z. | **vertagt**, siehe §2.5 |
| 6 | `layouts.py` | 288 Z. | `layouts.default_wrapper_class`, **zuletzt**, §2.6 |

### 2.1 `background_job_manager` zuerst

Der Manager nimmt jetzt eine schlichte `job_id` und fasst kein Job-Objekt an.

**Korrigiert:** `track_task_name` gehört hier auf **`True`**, nicht auf `False`. Grund,
gemessen: dein `submit_computation_job` ruft `submit_named_job`, und das verdrahtet
`track_task_name=True` fest. Mit `False` verlierst du still den Backend-Write, den die
Worker-Management-Seite liest, wenn ein widerrufener Task seinen Namen nicht mehr selbst
meldet; er erscheint dann als "Unknown". Das ist kein cosmonaut-Spezifikum, beide Apps
registrieren den Tasknamen seit immer.

**Es passt nur ein Wrapper.** `submit_computation_job(job)` wandert auf `submit_job`.
`submit_update_db_task` und `submit_cleanup_task` nehmen **keine** Job-ID und bleiben auf
`submit_named_job`, so wie dessen Docstring es sagt. Der Schritt ist damit eine
Aufrufstelle, nicht drei.

Trotzdem zuerst, weil §2.3 und §2.4 darauf aufbauen und er allein klein ist.

### 2.2 `error_handling` mit `on_unhandled`

`handle_error` ist jetzt `handle_error(error, *, on_unhandled=None)`, keyword-only. Die
Framework-Version importiert **niemals** einen Mailversand; du reichst deinen hinein:

```python
Dash(..., on_error=partial(handle_error, on_unhandled=notify))
```

Deine Maintainer-Mail sitzt in `error_handling.py:22` (`send_mail`-Import) und wird im
Handler gerufen. Genau die wird zum Hook. **Wenn du sie vergisst, fallen die
Maintainer-Mails still aus**: kein Importfehler, kein Testfehlschlag. Schreib dir einen
Test dafür.

Domänenseitig bleiben deine eigenen Exceptions und die `error_responds_dict`-Einträge
dazu.

**Die `FileValidationError`-Kollision ist deine Entscheidung, nicht die des Frameworks.**
Das Framework definiert die Klasse weiter; du importierst zusätzlich eine gleichnamige
aus `soil_moisture_prediction.input_file_parser`. Entweder fängst du beide, oder der
Upload-Pfad wrappt die SMP-Exception in die Framework-Exception. **Nicht stillschweigend
überschreiben**, sonst greift das `except` im Upload-Callback nicht mehr. Die Begründung
zum Muster steht in `../cosmo-suite/docs/conventions/error_handling.md`.

### 2.3 `job.py` erfüllt `BaseJob`

`cosmo_suite.base_job.BaseJob` ist ein Vertrag über fünf Mitglieder: `job_id` (als
**Property**, weil die Apps es unterschiedlich ablegen), `save`, `delete`, `submit`,
`time_to_live`. Konstruktion, Arbeitsverzeichnis, Log-Refresh und alle Domänenmethoden
bleiben bei dir. Log-Refresh ist absichtlich **nicht** Teil des Vertrags.

Dein `Job` erbt künftig von `BaseJob` statt eigenständig zu sein. 807 Zeilen bleiben
größtenteils stehen; es geht um den Vertrag, nicht um Verlagerung.

**Der Tippfehler.** Der Vertragsname ist `time_to_live`. Bei dir heißt es
`time_to_life`, an **sechs** Stellen: `job.py` einmal, `pages/submission.py` fünfmal. Das
Framework hält einen Deprecated-Alias vor (`cosmo_suite/job.py:374`), du kannst also in
zwei Schritten umstellen: erst den Vertrag erfüllen, dann die sechs Stellen umbenennen.
Nicht beides in einem Commit.

### 2.4 `files_route`

`serve_files(app, *, job_class=Job)` nimmt jetzt deine Job-Klasse. Damit fällt der Grund
weg, der die 97 Zeilen hier gehalten hat.

Beachte: `serve_files` braucht über den Vertrag hinaus `working_dir` auf der Job-Klasse,
das steht in seinem Docstring. Prüfe, dass deine Klasse das hat, bevor du umstellst.

### 2.5 vertagt: nicht in diesem Slice

**Nicht anfassen.** Dieser Schritt ist mit `v0.5.0` nicht ausführbar, und zwar aus
Framework-Gründen. Ausgeführt, nicht vermutet:

```python
from cosmo_suite.db_manager import Base
class AppJobTable(Base):
    __tablename__ = "jobs"
# InvalidRequestError: Table 'jobs' is already defined for this MetaData instance.
```

`Base` und die konkrete `JobTable` liegen im selben Modul: wer die Registry importiert,
registriert die Tabelle mit. Die Anweisung "definiere deine `JobTable` weiter selbst,
aber auf der Framework-`Base`" kann deshalb nicht funktionieren.

Dazu ist die Schnittmenge falsch geschnitten. Sie führt `input_data` und `logs`, die
cosmonauts `jobs` nicht hat, und eine fehlende Spalte ist genau der Fall, der zur
Laufzeit knallt. Die echte Schnittmenge über alle drei Konsumenten sind sechs Spalten.

Beides wird im Framework repariert, siehe
`../cosmo-suite/docs/plan/slice2b-framework-batch4.md` (Ziel `v0.6.0`): `JobColumns` als
Mixin, jede App deklariert ihre konkrete Klasse selbst, `DbManager.job_table` als Naht.
Danach kommt dieser Schritt als eigener kleiner Slice zurück.

Der Zwei-Engine-Zustand bleibt bis dahin bestehen. Das ist bekannt und dokumentiert.

### 2.6 `layouts` zuletzt

`layouts.default_wrapper_class` ist ein Modul-Attribut, das **vor** dem Import der
Framework-Seiten gesetzt wird (`cosmo_suite/layouts.py:246`). Setzen per Zuweisung an das
Modul, nicht per `from … import`, ein importierter Name bindet den Wert, nicht die
Variable. Der Kommentar an der Stelle sagt das auch.

Zuletzt, weil Layout die Seite ist, auf der ein Fehler am sichtbarsten und am
schwersten zuzuordnen ist.

---

## 3. Was das bringt

Rund **2.600 weitere Zeilen** in Reichweite, kumuliert mit Slice 1 also etwa 4.900. Die
Zahl ist aber nicht das Ziel: `error_handling`, `job` und `postgres_manager` bleiben
größtenteils bei dir, es geht um die Verträge. Berichte am Ende die **gemessene** Zahl
(`git diff --stat` gegen den Basis-Commit), nicht die geschätzte.

---

## 4. Vorgemessene Stolperstellen

### 4.1 Der Duplicate-Callback, den du schon kennst

Diese App hat ihn in Slice 1b getroffen: eine Framework-Seite zu importieren bringt
`cosmo_suite.layouts` mit, das einen Callback auf einer ID registriert, die du schon
belegt hattest. Dash bricht daraufhin die **gesamte** Callback-Registry ab, und das
Symptom erscheint auf einer anderen Seite als die Ursache. Gelöst wurde es, indem der
lokale Callback entfiel.

§2.6 ist genau die Stelle, an der das wieder auftreten kann. Die Regel dahinter steht
jetzt in `framework_page_imports.md`.

### 4.2 Port 8080

Cosmonauts Suite bindet denselben Port. Die übrigen Test-Services liegen inzwischen auf
eigenen Ports (siehe `../cosmo-suite/docs/plan/local-port-allocation.md`), aber Dash
kollidiert weiter. Mit dem cosmonaut-Agenten serialisieren. Eine Kollision sieht wie
Setup-ERRORs oder serverlose e2e-Tests aus, nicht wie ein inhaltlicher Fehlschlag.

### 4.3 `test_documentation_version` ist stillgelegt

Der Release-Job schreibt `doc_version.txt` selbst, der Test kann also nicht mehr
auslösen. Nicht darauf verlassen, dass er eine veraltete Doku meldet. Der belastbare
Ersatz wäre ein Hash über die Doku-Quellen; das ist bewusst nicht Teil dieses Slice.

---

## 5. Ausdrücklich NICHT in diesem Slice

- **Screenshots und `documentation.md` regenerieren.** Louis macht das selbst.
- **`ruff format` repo-weit.** Hier ist beides sauber, bitte so halten.
- **Der Doku-Frische-Hash** aus §4.3.
- **Domänenmodule:** `doc_generator`, `email_service`, `form_template_factory`,
  `map_utils`, `screenshot_generator`, `timeio_*`, `utils`.

---

## 6. Definition of Done

- Pin auf `v0.5.0`, `uv lock`, ein grüner CI-Lauf.
- Die sechs Punkte aus §2 erledigt oder mit begründeter Ausnahme dokumentiert.
- **Ein Test, der belegt, dass `on_unhandled` gerufen wird.** Das ist die eine Änderung,
  die still ausfällt.
- `./run_pytest.sh` grün, Baseline 20/20.
- Am **laufenden** System durchgeklickt: Logs, Job Management, Worker Management,
  Download, und einmal ein Job-Submit.
- Zwei-Engine-Zustand aufgelöst, oder dokumentiert, warum nicht.
- Gemessene Zeilenzahl berichten.

---

## 7. Konventionen

`CLAUDE.md` und `docs/conventions/*` gelten: keine `dict.get()`, kein bare
`except Exception`, keine Inline-Imports, HTML-IDs nur aus Konstanten, kein Inline-CSS.

Aus `docs/knowledge/concepts/dynamic-forms.md`: Callbacks werden zur Importzeit
verdrahtet, fehlt ein referenziertes Feld im DOM, validiert das **ganze** Formular nicht
mehr. Und React-Fehler #31 durch verschachtelte Listen, ein Wrapper-`Div` pro
`InputField`.
