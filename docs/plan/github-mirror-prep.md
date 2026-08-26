# COSMOPOLITAN — Vorbereitung für den öffentlichen GitHub-Mirror (C2)

**Repo:** `cosmopolitan` · **Anlass:** SoftwareX-Metadatum C2
**Erstellt:** 2026-08-12

---

## 0. Warum

C2 der Metadaten-Tabelle verlangt wörtlich: *„codebase.helmholtz is not acceptable …
Please note that a GitHub repository is mandatory. We will not proceed with your paper
otherwise."* Die Arbeit läuft weiter auf GitLab; GitHub wird ein **Push-Mirror**.

Der eigentliche Blocker ist nicht der Mirror, sondern der **Dependency-Pin**: diese App
pinnt `cosmo-suite @ git+https://codebase.helmholtz.cloud/…`. Auf einem öffentlichen
Mirror ist diese URL für Außenstehende nicht erreichbar — der veröffentlichte Code wäre
**nicht installierbar**, und genau das behauptet §2.4 des Papers („reproducible
installation with minimal configuration effort").

**Keine Secrets im Weg.** Geprüft: alle Secret-Felder in `env_dev_prod` sind leer, die
übrigen env-Dateien enthalten Platzhalter. Nur Mailrelay-Host, Port, Kontoname und
Absender tragen Werte — Konfiguration, keine Zugangsdaten. Ein Mirror mit **voller
Historie** ist also unbedenklich; kein History-Rewrite nötig.

---

## 1. Vorbedingung (Louis, nicht der Agent)

Das Ziel steht fest: **`github.com/Helmholtz-UFZ`** (Team `cosmo-suite` unter MET). Offen
ist nur noch Louis' Teil:

1. ~~Repos in der Org anlegen~~ — ✅ erledigt: `Cosmonaut`, `Cosmopolitan`, `CosmoSuite`, alle public und leer, Team `Cosmo-Suite` als Admin.
2. Push-Mirror in GitLab einrichten: *Settings → Repository → Mirroring repositories*,
   Richtung **Push**, GitHub-PAT mit `repo`-Scope, *„Mirror only protected branches"*
   aktiviert.
3. Nach dem ersten Sync verifizieren, dass **Tag `v0.4.0` bei cosmo-suite angekommen
   ist** — ohne den Tag scheitert der Pin unten.

Umfang, Release-/Zenodo-Schritt und Verifikation stehen kanonisch in
[`../../../cosmo-suite/docs/plan/github-mirror-setup.md`](../../../cosmo-suite/docs/plan/github-mirror-setup.md)
— dort **nicht** duplizieren, nur nachlesen: gespiegelt werden `main` **und Tags**,
keine Feature-Branches; ein Tag allein erzeugt keinen Release; der Push-Mirror
überschreibt, also niemals direkt auf GitHub committen.

---

## 2. Version/Tag-Mismatch geradeziehen (zuerst) — ✅ **ERLEDIGT**

> Stand 2026-08-18: `pyproject.toml` sagt `0.2.3`, letzter Tag ist `0.2.3` — Datei und
> Tag stimmen überein. **Punkt 3 unten (die Ursache) bitte gegenprüfen:** wenn der Job
> `bump_version_for_cluster` weiterhin nur `values.yaml` schreibt, driftet es beim
> nächsten Deployment erneut, und C1 stimmt nur bis dahin.


`pyproject.toml` sagt `version = "0.1.7"`, der letzte Tag ist **`0.2.3`**. Das ist
derselbe Fehlerklasse wie im Framework (dort `0.1.0` bei Tag `v0.2.0`) — nur fällt es
hier direkt in C1 der Metadaten-Tabelle: was gespiegelt wird, ist die Zahl, die im Paper
steht, und ein Reviewer kann sie in zwei Klicks widerlegen.

1. Klären, welche Zahl stimmt. Der Tag `0.2.3` ist mutmaßlich der Wahrheitswert (die
   Tags werden automatisch beim Cluster-Deployment erhöht, siehe die
   `automatically increased tag-version`-Commits), `pyproject.toml` ist hinterhergefallen.
2. `version` auf den Stand ziehen und **den nächsten Tag daraus ableiten**, nicht wieder
   danebenlegen. Vorschlag: `version = "0.2.4"` und `git tag 0.2.4` in einem Commit,
   damit Datei und Tag ab jetzt identisch sind.
3. **Die Ursache abstellen — ohne das ist Schritt 1–2 kosmetisch.**

   Lokalisiert: `.gitlab-ci.yml:161`, Job `bump_version_for_cluster`. Er feuert auf einen
   **Tag-Push** (`$CI_COMMIT_TAG =~ /^\d+.\d+.\d+/`), schreibt die Tag-Version nach
   `deployments/ufz/stage/values.yaml`, committet mit `-o ci.skip` — und **fasst
   `pyproject.toml` nie an**. Verifiziert: der letzte solche Commit berührte
   ausschließlich `values.yaml`.

   Es ist also kein Fehler in der Automatik, sondern: **niemand besitzt die
   Versionsdatei.** Ein Mensch taggt, die CI verteilt den Tag ans Deployment, die Datei
   bleibt stehen.

   **Gewählter Fix (Entscheidung Louis, pragmatisch):** denselben Job zusätzlich
   `pyproject.toml` aus `$CI_COMMIT_TAG` schreiben lassen — eine Zeile im bestehenden
   `script:`, vor `git add`. Danach können Datei und Tag nicht mehr driften.

   ```yaml
   - 'sed -i "s/^version = .*/version = \"${CI_COMMIT_TAG}\"/" pyproject.toml'
   - "git add deployments/ufz/stage/values.yaml pyproject.toml"
   ```

   Der `-o ci.skip` am Push bleibt — sonst löst der Commit eine neue Pipeline aus.

   *(Sauberer wäre die Gegenrichtung: `pyproject.toml` ist die Quelle, der Tag wird daraus
   abgeleitet. Das ist ein Umbau der Release-Mechanik und bewusst nicht jetzt.)*

---

## 3. Pin auf GitHub umstellen

```toml
# pyproject.toml → [project].dependencies
"cosmo-suite @ git+https://github.com/Helmholtz-UFZ/CosmoSuite@v0.4.0",
```

Dann `uv lock`.

**Das wird einfacher, nicht komplizierter:** GitHub ist öffentlich erreichbar, also
entfällt die Auth über `CI_JOB_TOKEN` gegen das interne GitLab. Eine URL, die überall
funktioniert — im CI, lokal, und bei jedem Außenstehenden.

Drei Dinge dabei prüfen:

1. ~~Egress der GitLab-Runner nach github.com~~ — **erledigt, 2026-08-12.** Gemessen auf
   beiden Runner-Pools: Default-Pool grün, `hifis`-Pool grün, **und** ein echter
   `docker build` mit dind, in dem `uv` eine `git+https://github.com/…`-Dependency
   auflöst, ebenfalls grün. Das war der einzige echte Risikopunkt; er ist weg. Der
   Wegwerf-Branch `egress-test` und die temporären Jobs können gelöscht werden.
2. `[tool.hatch.metadata] allow-direct-references = true` bleibt nötig (steht schon drin).
3. `git` muss im CI-Image installiert sein — `uv export` schreibt die Dependency als
   `git+https://`-URL. Steht in der Framework-README; hier verifizieren.

*(Der PyPI-Ausweg — cosmo-suite veröffentlichen und `cosmo-suite==0.4.0` pinnen — wird
nach der Egress-Messung nicht mehr gebraucht. Bleibt als Option, falls sich die
Netzpolicy ändert.)*

---

## 3b. Reihenfolge: was jetzt geht, was auf den Mirror wartet

**Phase A — sofort, unabhängig vom Mirror:**
§2 (Version/Tag + Ursache), §4 (Grep-Durchgang), §4.1 (Mail-Bereinigung), §5 (Copyright,
`LICENSE`). Das ist der Großteil des Plans.

**Phase B — sobald die Repos in der Org existieren und der Mirror läuft:**
§3 (Pin auf die GitHub-URL) und der README-Installationsabschnitt aus §5. Mehr nicht.

Phase A **nicht** blockieren, um auf Phase B zu warten. Die beiden Phasen dürfen in
getrennten Commits landen.

---

## 4. Grep-Durchgang vor dem ersten öffentlichen Push

Einmal durch den ganzen Baum, **inklusive Historie**, auf Dinge, die nicht nach außen
sollen:

```bash
# interne Hostnamen / Infrastruktur
grep -rniE 'ufz\.de|helmholtz\.cloud|intranet|10\.[0-9]+\.|192\.168\.' \
  --exclude-dir=.git --exclude-dir=.venv .
# Mailadressen von Kollegen
grep -rniE '[a-z.\-]+@[a-z.\-]+\.(de|com|org)' --exclude-dir=.git --exclude-dir=.venv .
# k8s / Deployment
ls deployment/ docker/ 2>/dev/null
```

Bewerten, nicht blind löschen:

### 4.1 Mail-Bereinigung (konkret, gemessen)

**Was NICHT das Problem ist:** die persönlichen Adressen. C8 der Metadaten-Tabelle
publiziert `john.anders@ufz.de, louis-ferdinand.trinkle@ufz.de` als Support-Kontakt — das
Paper veröffentlicht sie ohnehin. Sie aus dem Repo zu entfernen bringt für die Exposition
nichts.

**Was rausgehört — das Paar Dienstkonto + Relay:**

`EMAIL_USERNAME="soncosmo"` zusammen mit `EMAIL_SERVER="smtp.ufz.de"` steht in beiden
Apps und **nicht** im Paper. Ein gemeinsames Dienstkonto plus Relay-Host gehört nicht in
ein öffentliches Repo. Beide Werte in den getrackten Dateien durch Platzhalter ersetzen,
echte Werte in eine ignorierte `_priv`-Variante — dem Muster folgend, das cosmonaut mit
`env_dev_prod_priv` schon in der `.gitignore` hat.

Entwarnung dazu, damit die Dringlichkeit stimmt: **`env_prod` enthält gar keine
`EMAIL_PASSWORD`-Zeile**, `env_dev_prod` ist leer, die test/mock-Dateien tragen einen
4-Zeichen-Dummy. Ein Kontoname ohne Passwort ist kein Zugang — das ist Hygiene, kein
Notfall, und **kein** Grund für einen History-Rewrite.

**`MAINTAINER_EMAIL` bereinigen — Betriebsfehler, unabhängig vom Mirror:**

Der Wert lautet in mehreren env-Dateien noch `john…@ufz.de,louis-ferdinand.trinkle@ufz.de`.
Es gibt zwar den Commit „Remove Johns mail", der hat aber **nicht alle env-Dateien
erfasst**. John arbeitet nicht mehr am UFZ, also laufen Fehlermails teilweise in ein
Postfach, das niemand liest.

→ John aus **allen** `MAINTAINER_EMAIL`-Werten entfernen, in jeder getrackten env-Datei.
**John bleibt Autor des Papers und Contributor im Repo** — das betrifft ausschließlich
die operative Fehlermail-Adresse, nicht die Urheberschaft. Nicht mit §5
(Copyright/Contributors) verwechseln: dort bleibt er stehen.
- **k8s-Manifeste** mit internen Cluster-Namen: prüfen, ob sie öffentlich Sinn ergeben
  oder nur internen Kontext leaken.
- `codebase.helmholtz.cloud`-URLs in Doku und READMEs: die dürfen bleiben (das ist der
  Arbeitsort), aber Installationsanweisungen sollten auf GitHub zeigen.

**Wichtig:** Was hier gefunden wird, steckt auch in der Historie. Solange es keine
Zugangsdaten sind, ist das vertretbar — Infrastrukturdetails und Dienstadressen rechtfertigen
keinen History-Rewrite. Falls doch etwas Kritisches auftaucht: melden, nicht selbst
umschreiben.

---

## 5. Lizenz und Metadaten

- `LICENSE` vorhanden, EUPL-1.2, deckt sich mit C3 ✓
- `pyproject.toml` hat `license = { text = "EUPL-1.2" }` ✓
- **Copyright-Halter umstellen** (Entscheidung Louis, 2026-08-12): aktuell steht dort
  eine Privatperson („Copyright (c) 2025, John …"). Künftig **Institution als Halter,
  Personen als Contributors**:

  ```
  Copyright (c) 2025 Helmholtz-Zentrum für Umweltforschung GmbH – UFZ
  ```

  Die beteiligten Personen darunter als `Contributors:`-Zeile oder in einer eigenen
  `AUTHORS`-Datei — das gibt Anerkennung und ist gleichzeitig sachlich richtiger: nach
  §69b UrhG stehen dem Arbeitgeber die ausschließlichen Nutzungsrechte an Software zu,
  die Angestellte in Erfüllung ihrer Aufgaben schaffen. Das UFZ hält sie also
  wahrscheinlich ohnehin.

  **In allen drei Repos identisch.** Louis hat beim UFZ angefragt, ob es eine Vorgabe zum
  Halter gibt — kommt eine abweichende Antwort, gilt die. Bis dahin obige Form.
- README: der Installationsabschnitt muss auf die GitHub-URL zeigen, nicht auf GitLab —
  sonst liest ein Außenstehender eine Anleitung, die er nicht ausführen kann.

---

## 6. Definition of Done

- `version` in `pyproject.toml` und der neueste Tag stimmen überein; die Tag-Automatik
  hält sie künftig synchron (§2.3).
- Pin zeigt auf `github.com/Helmholtz-UFZ/CosmoSuite@v0.4.0`, `uv lock` aktualisiert.
- **Ein grüner CI-Lauf mit dem GitHub-Pin** — das ist die Abnahme, nicht ein lokales
  `uv sync`.
- `./run_pytest.sh` grün (Baseline 20/20).
- Grep-Durchgang dokumentiert: was gefunden wurde und was damit passiert ist.
- README-Installationsabschnitt zeigt auf GitHub.
- Fremde Werte (Mailrelay, Adressen) entweder Platzhalter oder bewusst freigegeben.

---

## 7. Was hier NICHT passiert

- **Kein History-Rewrite.** Keine Secrets gefunden, also kein Anlass.
- **Kein Wechsel der Lizenz.** EUPL-1.2 bleibt; nur der Copyright-Halter ist offen.
- **Kein Zenodo.** Die DOI-Verknüpfung („permanent link" in C2) macht Louis am
  GitHub-Release, nicht der Agent im Repo.
