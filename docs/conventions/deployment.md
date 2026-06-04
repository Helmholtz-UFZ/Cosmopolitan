# Deployment Conventions

Stage/prod run on Kubernetes (UFZ cluster, ArgoCD). This doc covers non-obvious
gotchas that don't surface in local docker-compose development.

## values.yaml is partly automated — re-tag after infra changes

The image tag in `deployments/ufz/stage/values.yaml` is **not** hand-maintained.
A scheduled GitLab CI pipeline (`build-latest-tag` → `bump_version_for_cluster`
in `.gitlab-ci.yml`) rebuilds the Docker image nightly and commits the new tag
back to `main`. The point is base-image / OS security patches without cutting a
new release — the daily image is `<tag>-YYYY.MM.DD`.

The catch: `build-latest-tag` does `git checkout <latest git tag>` and commits
**that tag's** `values.yaml` back to main (with `git pull --strategy-option=ours`).
The git tag almost always predates your latest infra edits, so:

> **Any change you make directly to `values.yaml` on main — `ingress.className`,
> annotations, resources, env vars, … — is silently reverted by the next nightly
> run, because the tag it checks out is older than your change.**

This is exactly what broke the ingress in #48: a `className: haproxy` edit on
main was reverted to `nginx` by the nightly, producing a self-signed
`Kubernetes Ingress Controller Fake Certificate` + 404 — while ArgoCD still
showed the app healthy.

### Rule

- **After any infra change to `values.yaml`, cut a new git tag** from main
  (`git tag 0.x.y` → push, or GitLab → Tags → New tag, target `main`). The tag
  pipeline rebuilds, and the nightly then checks out a tag that contains your
  change, so it stops reverting.
- Don't "fix" this by patching the nightly job to pull `values.yaml` from main
  mid-build — that pairs a main-`values.yaml` with an old-tag image and was
  rejected in review (#48). Re-tagging is the agreed workflow.

## Ingress: className must be `haproxy`

The UFZ cluster's working ingress controller is **haproxy**, not nginx. Both the
frontend and tileserver ingress in `values.yaml` must use:

```yaml
ingress:
  className: "haproxy"
  annotations:
    haproxy-ingress.github.io/config-backend: |
      http-response set-header 'X-Content-Type-Options' 'nosniff';
      # ...CSP etc.
```

With `className: "nginx"` the haproxy controller never claims the ingress;
requests fall through to a default nginx controller that serves the self-signed
fake certificate and then 404s. The tell-tale symptom: **fake certificate + 404
on every path, but ArgoCD healthy** → the className got reverted (see above).
This is the same setup as the sister project Cosmonaut.
