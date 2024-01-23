"""All routes of cosmopolitan."""

import logging
import os

from flask import current_app as app
from flask import redirect, render_template, request, send_from_directory, url_for
from werkzeug.exceptions import BadRequestKeyError

from cosmopolitan_app.config import WEB_WORK_DIR
from cosmopolitan_app.cosmopolitan_job import CosmopolitanJob
from cosmopolitan_app.cosmopolitan_job_form import CosmopolitanJobForm
from cosmopolitan_app.dash_component.dynamic_plots import base_path as result_path
from cosmopolitan_app.utils import (
    SubmittedException,
    send_finished_mail,
    send_submission_mail,
)


@app.route("/")
def start():
    """Start page."""
    return render_template("html/content/start.html")


@app.route("/submission", methods=["GET", "POST"])
def search_submission():
    """Route to be accessed by navbar search form."""
    logging.info("Search submisison")
    try:
        return redirect(url_for("submission", job_id=request.form["job_id"]))
    except BadRequestKeyError:
        return redirect(url_for("submission", job_id=""))


@app.route("/submission/", defaults={"job_id": ""})
@app.route("/submission/<job_id>", methods=["GET", "POST"])
def submission(job_id):
    """Site for submitting and presenting progress and results of a job."""
    logging.info("Submisison site")
    job = CosmopolitanJob(job_id=job_id)
    if not job.submitted:
        job.submit()
        send_submission_mail(job)
    else:
        job.check_status()
    if job.status not in ["FAILED", "COMPLETED"]:
        reload_delay = 5
    else:
        send_finished_mail(job)
        reload_delay = None

    return render_template(
        "html/job/submission.html",
        job=job,
        reload_delay=reload_delay,
        result_path=result_path,
    )


@app.route("/confirm/<job_id>")
def confirm(job_id):
    """Confirm input and submit."""
    logging.info(f"Confirm submisison for job {job_id}")
    job = CosmopolitanJob(job_id=job_id)
    if job.submitted:
        raise SubmittedException
    return render_template("html/job/confirm.html", job=job)


@app.route("/input/<job_id>", methods=["GET", "POST"])
def change_input(job_id):
    """Change input of an unsubmitted job."""
    logging.info(f"Make changes to job {job_id}")
    job = CosmopolitanJob(job_id=job_id)
    if job.submitted:
        raise SubmittedException
    return render_template("html/job/input.html", form=job.form)


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
            logging.info("Form is valid")
            job = CosmopolitanJob(form=form)
            job.save()
            return redirect(url_for("confirm", job_id=job.job_id))
    return render_template("html/job/input.html", form=form)


@app.route("/documentation")
def documentation():
    """Show documentation."""
    return render_template("html/content/documentation.html")


@app.route("/results/<job_id>/<file_name>")
def result_file(job_id, file_name):
    """Serve result files."""
    logging.info(f"Visiting /results/{job_id}/{file_name} to result_file()")
    output_dir = os.path.join(WEB_WORK_DIR, job_id)
    return send_from_directory(output_dir, file_name)
