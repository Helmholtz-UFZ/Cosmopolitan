"""Flask app that handles the Cosmopolitan Webserver."""

import os

from flask import Flask, render_template, request, redirect
from flask_wtf.csrf import CSRFProtect

from cosmopolitan_job import CosmopolitanJob
from config import vprint
from cosmopolitan_job_form import CosmopolitanJobForm, json_load_4_jinja
from db_manager import JobNotFound

app = Flask(__name__)

csrf = CSRFProtect(app)

# CSRF key
app.config["SECRET_KEY"] = os.urandom(32)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500 Mb limit

app.jinja_env.globals.update(json_loads=json_load_4_jinja)


@app.route("/")
def hello_geek():
    """Hello world."""
    return "<h1>Hello from Flask & Docker</h1>"


@app.route("/submission/<job_id>", methods=["GET", "POST"])
def submission(job_id):
    """Site for submitting and presenting progress and results of a job."""
    try:
        job = CosmopolitanJob(job_id=job_id)
    except JobNotFound:
        return render_template("html/errors/job_not_found_error.html", job_id=job_id)
    if not job.submitted:
        job.submit()
    return render_template("html/submission/submission.html", job=job)


@app.route("/confirm/<job_id>", methods=["GET", "POST"])
def confirm(job_id):
    """Confirm input and submit."""
    vprint(f"Confirm submisison for job {job_id}", verbose_level=1)
    try:
        job = CosmopolitanJob(job_id=job_id)
    except JobNotFound:
        return render_template("html/errors/job_not_found_error.html", job_id=job_id)
    if job.submitted:
        return render_template("html/errors/job_submitted_error.html", job_id=job_id)
    return render_template("html/input/confirm.html", job=job)


@app.route("/input/<job_id>", methods=["GET", "POST"])
def change_input(job_id):
    """Change input of an unsubmitted job."""
    vprint(f"Make changes to job {job_id}", verbose_level=1)
    try:
        job = CosmopolitanJob(job_id=job_id)
    except JobNotFound:
        return redirect("/input")
    if job.submitted:
        return render_template("html/errors/job_submitted_error.html", job_id=job_id)
    job.delete()
    return render_template("html/input/input.html", form=job.form)


@app.route("/input", methods=["GET", "POST"])
def input():
    """Input site for the job."""
    # Make new job and form if empty request form
    if len(request.form) == 0:
        vprint("Input for new job", verbose_level=1)
        job = CosmopolitanJob()
        form = job.form
    # If form was submitted validate
    else:
        form = CosmopolitanJobForm(new=False)
        vprint(f"Check form {form.job_id.data}", verbose_level=1)
        if form.validate_on_submit():
            job = CosmopolitanJob(form=form)
            job.save()
            return redirect(f"/confirm/{job.job_id}")
    return render_template("html/input/input.html", form=form)


@app.route("/privacy")
def privacy():
    """Return privacy notes."""
    # TODO
    return render_template("html/content/privacy.html")


if __name__ == "__main__":
    app.run()
