<h1 align="center">COSMOPOLITAN</h1>
<h2 align="center"><strong>COS</strong><small>mic ray based soil </small><strong>MO</strong><small>isture </small><strong>P</strong><small>redicti</small><strong>O</strong><small>n </small><strong>LI</strong><small>ve descicion </small><strong>T</strong><small>ree </small><strong>AN</strong><small>alysis</small></h2>
<img src="cosmopolitan_app/static/start_banner.webp" alt="Welcome" style="width: 33.33%; margin: auto; display: block;">

This is a web service for analysing cosmic ray data to predict soil moisture
content. The prediction is based on a random forest model and aims to become a
to become a live soil moisture map of Germany.

The model was developed by Ségolène Dega and the scripts are available in this
[repository](https://git.ufz.de/dega/sm_prediction).

![Welcome](cosmopolitan_app/static/start_banner.webp)

### Framework

The web service is based on `flask` see
`cosmopolitan_app/cosmopolitan_web_server.py`. The main input validation is with
`flaskWTF` see `cosmopolitan_app/cosmopolitan_job_form.py`. For the data storage
an exchange with the compute cluster uses a postgres DB, see
`cosmopolitan_app/db_manager.py`. Logging in production is also done in the
postgres DB, see `cosmopolitan_app/logger.py`. Communication with the cluster is
handled by a `SLURM REST API`, see methods of the `CosmopolitanJob` in
`cosmopolitan_app/cosmopolitan_job.py`. For interactive components the `dash`
framework is used and are located in `cosmopolitan_app/dash_component/`.

### Build and development

The web service is built as a Docker container intended to run on a
Cubernet cluster. The build is organised in a CI pipeline on gitlab, see
`.gitlab-ci.yml` and the build instructions in `Dockerfile`. The docker
container can be built locally using the
`docker compose up`. In `docker-compose.yml` the build and the run settings are
defined. Before you can do this, `cp .env_dev .env` and set the
empty variables. The server needs credentials to connect to the mail server,
postgres DB and the SLURM REST API, without them he will not be able to start.

The `FLASK_DEBUG` variable also controls
if flask is started in debug mode (easier logging, reloading scripts) and
GUNICORN' controls whether the production server is used. To make development
easier `docker compose` will bind the current repository to the docker container. So
that if `FLASK_DEBUG=1`, the web server is automatically reloaded when one of the
scripts in `cosmopolitan_app/*` are changed.

The webserver is deployed using `gunicorn`. If the environment variable
`GUNICORN=1` docker will start the image with gunicorn workers.

The code base tries to adhere to the `flake8` standard and is formated with
`Black`. To ensure styling coherence the precommit configuration in
`.pre-commit-config.yaml` should be used. 

### Versions

The gitlab CI will always produce a "nightly" build of the latest `main` branch
called `latest`. To make a new release, create a git tag of the form 0.0.1,
1.2.3, ... and commit it. This will trigger a new build of the web server
with a new version tag.
