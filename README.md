<div>
<h1 align="center">COSMOPOLITAN</h1>
<h2 align="center"><strong>COS</strong><small>mic ray based soil </small><strong>MO</strong><small>isture </small><strong>P</strong><small>redicti</small><strong>O</strong><small>n </small><strong>LI</strong><small>ve </small><strong>T</strong><small>ree </small><strong>AN</strong><small>alysis</small></h2>
<p align="center">
	<img src="cosmopolitan_app/static/start_banner.png" alt="Welcome" width="30%">
</p>
</div>
This is a web service for analysing cosmic ray data to predict soil moisture
content. The prediction is based on a random forest model and aims to become a
to become a live soil moisture map of Germany.

The model was developed by Ségolène Dega and the scripts are available in this
[repository](https://git.ufz.de/dega/sm_prediction).

## Framework

The web service is based on `flask` see
`cosmopolitan_app/cosmopolitan_web_server.py`. The main input validation is with
`flaskWTF` see `cosmopolitan_app/cosmopolitan_job_form.py`. For the data storage
an exchange with the compute cluster uses a postgres DB, see
`cosmopolitan_app/db_manager.py`. Logging in production is also done in the
postgres DB, see `cosmopolitan_app/logger.py`. Communication with the cluster is
handled by a `SLURM REST API`, see methods of the `CosmopolitanJob` in
`cosmopolitan_app/cosmopolitan_job.py`. For interactive components the `dash`
framework is used and are located in `cosmopolitan_app/dash_component/`.

## Build and development

### Production build

The web service is built as a Docker container intended to run on a
Kubernetes cluster. The build is organised in a CI pipeline on gitlab, see
`.gitlab-ci.yml` and the build instructions in `docker/prod.Dockerfile`.

```bash
docker pull git.ufz.de:4567/andersj/som-web:latest
docker run -e EMAIL_PASSWORD=$EMAIL_PASSWORD \
    -e FLASK_PORT="$FLASK_PORT" \
    -e CLUSTER_TOKEN="$CLUSTER_TOKEN" \
    -e DB_PW="$DB_PW" \
    -p "$FLASK_PORT:$FLASK_PORT" \
    git.ufz.de:4567/andersj/som-web
```

### Local build for development

#### tl;dr

```bash
cp .env_dev_mock .env
docker compose up
# or
./auxilary_scripts/dev_up.sh mock
```

#### More details

For development, the project can be built and started with either mock-up
servers or with a connection to the real services. The example above starts the
web server with mock-up servers. This will not send emails, change the database
or start jobs in the cluster. Another option is to develop with a connection to
the real services. For this you need to add credentials, the quickest way is: 

```bash
cp ./.env_dev_prod ./.env_dev_prod_priv
# Add the credentials with your editor
$EDITOR ./.env_dev_prod_priv
./auxilary_scripts/dev_up.sh prod
```

For the development there are four important variable in `.env_dev_*`. 

 1. `GUNICORN` controls if the web service is started with the production server.
 2. For debugging the Flask server use `FLASK_DEBUG` (easier logging, reloading
    scripts). This will only work if `GUNICORN=0`.
 3. The web server uses the library of the git repository `sm_prediction` for
    plotting. If you wish to make ongoing development you can do so by
    specifying the branch with `SM_BRANCH`.

To make development easier `docker compose` will bind the current repository to the
docker container. So that if `FLASK_DEBUG=1`, the web server is automatically reloaded
when one of the scripts in `cosmopolitan_app/\*` are changed.

The code base tries to adhere to the `flake8` standard and is formatted with
`Black`. To ensure styling coherence the pre commit configuration in
`.pre-commit-config.yaml` should be used. 

### Mock-up outside services

The web service relies on three external services 

 1. Mail server
 2. Postgres DB
 3. SLURM REST API

For two of the services a mock-up web server exist which allow to develop and test
without access to the services. Currently the SLURM REST API can not be mocked.

#### Mail server

The [MailHog](https://github.com/mailhog/MailHog) service is used to catch
emails. When the web service is running you 

### Versions

The gitlab CI will always produce a "nightly" build of the latest `main` branch
tagged `latest`. To make a new release, create a git tag of the form 0.0.1,
1.2.3, ... and commit it. This will trigger a new build of the web server
with a new version tag.
