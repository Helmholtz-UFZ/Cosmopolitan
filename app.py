"""Flask app that handles the Cosmopolitan Webserver."""

import os
import shutil
import smtplib
import traceback
from datetime import date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import (
    Flask,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.exceptions import HTTPException, NotFound

from config import (
    EMAIL_PASSWORD,
    EMAIL_PORT,
    EMAIL_SENDER,
    EMAIL_SERVER,
    EMAIL_USERNAME,
    WEB_INPUT_DIR,
    WEB_OUTPUT_DIR,
    WEB_UPLOAD_DIR,
    ssh_call,
)
from cosmopolitan_job import CosmopolitanJob
from cosmopolitan_job_form import CosmopolitanJobForm, json_load_4_jinja
from db_manager import DataBaseManager, JobNotFound
from logger import get_logger

app = Flask(__name__)

csrf = CSRFProtect(app)

# CSRF key
app.config["SECRET_KEY"] = os.urandom(32)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024 * 1024  # 5 Gb limit

app.jinja_env.globals.update(json_loads=json_load_4_jinja)

logger = get_logger(app.debug)


@app.errorhandler(Exception)
def handle_exception(e):
    """
    Handle exceptions gracefully within the Flask application.

    This function is an error handler for Exception types and takes appropriate action
    based on the type of exception encountered. It logs the error and returns an HTTP
    response accordingly. In depug mode it simply reraises the error and allows
    werkzeuge to handle the error.


    Parameters:
        e (Exception): The exception that triggered this handler.

    Returns:
        HTTPException or tuple: Depending on the type of exception, this function
        returns an appropriate HTTPException or a tuple containing a rendered error
        template and a 500 status code.

    Note:
        This function should be registered as an error handler in the Flask app
        using `@app.errorhandler(Exception)`.
    """
    if app.debug:
        raise e

    if isinstance(e, HTTPException):
        return e

    route = request.url_rule
    route_function = request.endpoint

    logger.info("Handle exception")
    error = traceback.format_exc()
    content = (
        f"Unexpected error in { route } using { route_function }:\n"
        f"{error}\n"
        f"PID={os.getpid()}\n"
    )
    logger.error(content)
    return render_template("html/errors/internal_error.html"), 500


def clean_up():
    """Delete jobs older than a day and older than two months and their directories."""
    logger.info("Start cleaning up.")
    db_manager = DataBaseManager()

    # Define the time thresholds
    two_day_ago = date.today() - timedelta(days=2)
    two_months_ago = date.today() - timedelta(days=60)

    jobs = db_manager.list_jobs()
    kept_jobs = []

    for job_id, (start_date, submitted) in jobs.items():
        logger.debug(f"Check job {job_id}.")
        if not submitted and start_date < two_day_ago:
            logger.debug("Job was not submit and is older than two days.")
            db_manager.delete_job(job_id)
        elif start_date < two_months_ago:
            logger.debug("Job older than two month.")
            db_manager.delete_job(job_id)
        else:
            logger.debug("Job will be kept.")
            kept_jobs.append(job_id)

    # Delete directories locally
    logger.info("Clean up directorys locally.")
    for directory in [WEB_INPUT_DIR, WEB_UPLOAD_DIR, WEB_OUTPUT_DIR]:
        for dir_name in os.listdir(directory):
            dir_path = os.path.join(directory, dir_name)
            if os.path.isdir(dir_path) and dir_name not in kept_jobs:
                shutil.rmtree(dir_path)

    # Delete work directories on cluster
    logger.debug("Clean up directorys on cluster.")
    old_jobs = [
        job_id
        for job_id in ssh_call("list_work_dir.sh").split()
        if job_id not in kept_jobs
    ]

    if len(old_jobs) > 0:
        ssh_call(f"delete_work_dir.sh { ' '.join(old_jobs) }")


def send_mail(recipient, subject, content):
    """Send an email using the provided details."""
    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = recipient
    msg["Subject"] = subject

    body = content
    msg.attach(MIMEText(body, "plain"))

    server = smtplib.SMTP(EMAIL_SERVER, EMAIL_PORT)
    server.starttls()
    server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
    server.sendmail(EMAIL_SENDER, recipient, msg.as_string())
    server.quit()


def send_submission_mail(job):
    """Send a notification email to the user that the job was submitted."""
    url = url_for("submission", job_id=job.job_id, _external=True)
    with open(
        "templates/emails/submission_email.txt", "r", encoding="UTF-8"
    ) as f_handle:
        content = f_handle.read().format(job_id=job.job_id, url=url)
    if job.email != "":
        send_mail(job.email, f'Job "{ job.job_id }" submitted', content)


@app.route("/")
def hello_geek():
    """Hello world."""
    raise ValueError
    return "<h1>Hello from Flask & Docker</h1>"


@app.route("/submission/<job_id>", methods=["GET", "POST"])
def submission(job_id):
    """Site for submitting and presenting progress and results of a job."""
    try:
        job = CosmopolitanJob(logger, job_id=job_id)
    except JobNotFound:
        return render_template("html/errors/job_not_found_error.html", job_id=job_id)
    if not job.submitted:
        job.submit()
        send_submission_mail(job)
    else:
        job.check_status()

    if job.status in ["RUNNING", "PENDING"]:
        reload_delay = 30
    else:
        reload_delay = None

    return render_template(
        "html/submission/submission.html", job=job, reload_delay=reload_delay
    )


@app.route("/confirm/<job_id>", methods=["GET", "POST"])
def confirm(job_id):
    """Confirm input and submit."""
    logger.info(f"Confirm submisison for job {job_id}")
    try:
        job = CosmopolitanJob(logger, job_id=job_id)
    except JobNotFound:
        return render_template("html/errors/job_not_found_error.html", job_id=job_id)
    if job.submitted:
        return render_template("html/errors/job_submitted_error.html", job_id=job_id)
    return render_template("html/input/confirm.html", job=job)


@app.route("/input/<job_id>", methods=["GET", "POST"])
def change_input(job_id):
    """Change input of an unsubmitted job."""
    logger.info(f"Make changes to job {job_id}")
    try:
        job = CosmopolitanJob(logger, job_id=job_id)
    except JobNotFound:
        return redirect("/input")
    if job.submitted:
        return render_template("html/errors/job_submitted_error.html", job_id=job_id)
    job.delete()
    return render_template("html/input/input.html", form=job.form)


@app.route("/input", methods=["GET", "POST"])
def input_job():
    """Input site for the job."""
    # Make new job and form if empty request form
    if len(request.form) == 0:
        logger.info("Input for new job")
        job = CosmopolitanJob(logger)
        form = job.form
    # If form was submitted validate
    else:
        form = CosmopolitanJobForm(logger, new=False)
        logger.info(f"Check form {form.job_id.data}")
        if form.validate_on_submit():
            job = CosmopolitanJob(logger, form=form)
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
    logger.info(f"Visiting /results/{job_id}/{file_name} to result_file()")
    try:
        output_dir = os.path.join(WEB_OUTPUT_DIR, job_id)
        return send_from_directory(output_dir, file_name)
    except NotFound:
        return render_template("html/errors/file_not_found.html")


if __name__ == "__main__":
    app.run()
