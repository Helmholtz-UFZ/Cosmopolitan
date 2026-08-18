# 0002 — Publish a public GitHub mirror, and what gets cleaned up first

**Status:** Accepted (Phase A). The dependency pin (Phase B) waits on the GitHub org name.
**Date:** 2026-08-12

---

## Context

SoftwareX metadata field C2 requires a GitHub repository: *"codebase.helmholtz is not
acceptable … a GitHub repository is mandatory."* Development stays on GitLab; GitHub
becomes a **push mirror**, so the same history becomes publicly readable.

That makes three things matter that did not matter internally:

1. **The dependency pin.** `pyproject.toml` pins
   `cosmo-suite @ git+https://codebase.helmholtz.cloud/…`, which an outsider cannot reach.
   The published code would not be installable — the exact claim §2.4 of the paper makes.
2. **The version number.** `pyproject.toml` said `0.1.7` while the newest tag was `0.2.3`.
   C1 of the metadata table publishes a version a reviewer can disprove in two clicks.
3. **Exposure.** Everything in the tree, including history, becomes readable.

## Decision

**Version.** `version` is set to `0.2.3`, matching the newest existing tag, rather than
bumping to `0.2.4` and tagging: a tag push builds and publishes production images and
rewrites the cluster values (`.gitlab-ci.yml`, `build` + `bump_version_for_cluster`). That
is a deployment, and it belongs to a human.

**The cause is fixed, not just the symptom.** Nobody owned the version file — a human tags,
CI hands the tag to the deployment, the file stays put. `bump_version_for_cluster` now
writes `pyproject.toml` from `$CI_COMMIT_TAG` as well. The write is guarded on a non-empty
tag, because that job also runs for `schedule` and `web` pipelines where `CI_COMMIT_TAG` is
empty and an unguarded `sed` would blank the version.

**Copyright holder is the institution, contributors are named.** `LICENSE` now reads
*Helmholtz-Zentrum für Umweltforschung GmbH – UFZ* instead of a private individual, with an
`AUTHORS` file crediting the people. Under §69b UrhG the employer holds the exclusive rights
to software written by employees in the course of their duties, so this is also the
factually correct attribution. The licence itself (EUPL-1.2) does not change.

**No history rewrite.** The exposure review below found no credentials.

## Exposure review (2026-08-12)

Grep over all tracked files for internal hosts, private ranges, and mail addresses.

| Finding | Verdict |
|---|---|
| `LICENSE`, `pyproject.toml` authors | Kept — authorship, and C8 publishes these addresses anyway |
| `test@ufz.de`, `test@test.de` in tests/mock env | Kept — dummy values |
| `cosmopolitan@ufz.de` (EMAIL_SENDER) | Kept — the application's own address, not a personal one |
| `EMAIL_USERNAME="soncosmo"` in test/mock env files | **Replaced** with `testuser`; those files never reach the real relay |
| `EMAIL_USERNAME="soncosmo"` + `EMAIL_SERVER="smtp.ufz.de"` in `env_prod`, `env_dev_prod` **and** `deployments/ufz/{prod,stage}/values.yaml` | **Open — see follow-up.** Production reads these from the k8s env, so cleaning only the env files changes nothing |
| `postgres.intranet.ufz.de`, `https://vip.s3.ufz.de` in `values.yaml` and `docker/init.sql` comments | **Open — Louis's call.** Internal topology, not credentials; unreachable from outside |
| `MAINTAINER_EMAIL` | Already clean. The plan expected John here; that cleanup had already happened |
| `soncosmo@frontend{1,2}.eve.ufz.de` as a commit author in history | Left. A hostname in an author field, no credential |

Nothing found justifies rewriting history.

## Alternatives considered

1. **Bump to `0.2.4` and tag it** (as the plan proposed) — rejected for now: the tag push
   deploys. Setting the file to the existing tag reaches the same end state (file and newest
   tag agree) without triggering a release.
2. **Publish `cosmo-suite` to PyPI and pin `cosmo-suite==0.4.0`** — not needed. Runner
   egress to github.com was measured on both pools on 2026-08-12, including a real
   `docker build` resolving a `git+https://github.com/…` dependency. Kept as a fallback if
   the network policy changes.
3. **Rewrite history to purge internal hostnames** — rejected. Infrastructure details are
   not credentials, and a rewrite would break every existing clone and the mirror setup.

## Consequences

- **Positive:** the published version is defensible, the file can no longer drift from the
  tag, and attribution is institutionally correct.
- **Trade-off:** the doc screenshots were not regenerated for `0.2.3` (that needs a running
  stack and a finished prediction job). `documentation.md` and `doc_version.txt` were
  regenerated from the page docstrings, which is what `test_documentation_version.py`
  checks; the screenshots show the same pages.
- **Follow-up, blocking a clean mirror:**
  1. **Service account + relay.** To remove `soncosmo`/`smtp.ufz.de` from the public repo,
     they must move out of `values.yaml` into the existing k8s secret
     (`custom-met-cosmopolitan.secrets`, which already holds `EMAIL_PASSWORD`). The secret
     must carry the new keys **before** the manifests reference them, or the pods break.
  2. **Internal hostnames** in `values.yaml` / `init.sql` comments: decide whether the
     deployment manifests belong in the public mirror at all.
  3. **Phase B:** repoint the pin to `github.com/<ORG>/cosmo-suite@v0.4.0` once the org
     exists, then a green CI run is the acceptance test — not a local `uv sync`.
  4. The existing SPDX headers say *"Helmholtz Centre for Environmental Research GmbH -
     UFZ"* (English) while `LICENSE`/`AUTHORS` now use the German form the plan prescribes.
     Harmonise once UFZ answers which form is official.
