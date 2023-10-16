"""All routes of cosmopolitan."""

import logging
import os

from flask import current_app as app
from flask import redirect, render_template, request, send_from_directory

from cosmopolitan_app.config import WEB_INPUT_DIR
from cosmopolitan_app.cosmopolitan_job import CosmopolitanJob
from cosmopolitan_app.cosmopolitan_job_form import CosmopolitanJobForm
from cosmopolitan_app.utils import clean_up, send_submission_mail


@app.route("/")
def hello_geek():
    """Hello world."""
    return "<h1>Hello from Flask & Docker</h1>"


@app.route("/submission/<job_id>", methods=["GET", "POST"])
def submission(job_id):
    """Site for submitting and presenting progress and results of a job."""
    job = CosmopolitanJob(job_id=job_id)
    if not job.submitted:
        job.submit()
        send_submission_mail(job)
    else:
        job.check_status()
    if job.status in ["RUNNING", "PENDING"]:
        reload_delay = 5
    else:
        reload_delay = None

    return render_template(
        "html/submission/submission.html", job=job, reload_delay=reload_delay
    )


@app.route("/confirm/<job_id>", methods=["GET", "POST"])
def confirm(job_id):
    """Confirm input and submit."""
    logging.info(f"Confirm submisison for job {job_id}")
    job = CosmopolitanJob(job_id=job_id)
    if job.submitted:
        return render_template("html/errors/job_submitted_error.html", job_id=job_id)
    return render_template("html/input/confirm.html", job=job)


@app.route("/input/<job_id>", methods=["GET", "POST"])
def change_input(job_id):
    """Change input of an unsubmitted job."""
    logging.info(f"Make changes to job {job_id}")
    job = CosmopolitanJob(job_id=job_id)
    if job.submitted:
        return render_template("html/errors/job_submitted_error.html", job_id=job_id)
    job.delete()
    return render_template("html/input/input.html", form=job.form)


@app.route("/input", methods=["GET", "POST"])
def input_job():
    """Input site for the job."""
    # Make new job and form if empty request form
    if len(request.form) == 0:
        logging.info("Input for new job")
        job = CosmopolitanJob()
        form = job.form
    # If form was submitted validate
    else:
        form = CosmopolitanJobForm(new=False)
        logging.info(f"Check form {form.job_id.data}")
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


@app.route("/clean_up")
def trigger_clean_up():
    """Trigger clean up."""
    # TODO
    clean_up()
    return "<h1>Putzen!</h1>"


@app.route("/results/<job_id>/<file_name>")
def result_file(job_id, file_name):
    """Serve result files."""
    logging.info(f"Visiting /results/{job_id}/{file_name} to result_file()")
    output_dir = os.path.join(WEB_INPUT_DIR, job_id)
    return send_from_directory(output_dir, file_name)
