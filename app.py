"""Flask app that handles the Cosmopolitan Webserver."""

import os
from datetime import date, timedelta
import shutil
import traceback

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    send_from_directory,
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.exceptions import HTTPException, NotFound

from logger import logger
from config import (
    vprint,
    ssh_call,
    SMTP_SERVER,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_PASSWORD,
    SENDER_EMAIL,
    INPUT_DIR,
    UPLOAD_DIR,
    OUTPUT_DIR,
)
from cosmopolitan_job import CosmopolitanJob
from cosmopolitan_job_form import CosmopolitanJobForm, json_load_4_jinja
from db_manager import DataBaseManager, JobNotFound

app = Flask(__name__)

csrf = CSRFProtect(app)

# CSRF key
app.config["SECRET_KEY"] = os.urandom(32)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024 * 1024  # 5 Gb limit

app.jinja_env.globals.update(json_loads=json_load_4_jinja)


@app.errorhandler(Exception)
def handle_exception(e):
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
    vprint("Start cleaning up.", verbose_level=1)
    db_manager = DataBaseManager()

    # Define the time thresholds
    two_day_ago = date.today() - timedelta(days=2)
    two_months_ago = date.today() - timedelta(days=60)

    jobs = db_manager.list_jobs()
    kept_jobs = []

    for job_id, (start_date, submitted) in jobs.items():
        vprint(f"Check job {job_id}.", verbose_level=3)
        if not submitted and start_date < two_day_ago:
            vprint("Job was not submit and is older than two days.", verbose_level=3)
            db_manager.delete_job(job_id)
        elif start_date < two_months_ago:
            vprint("Job older than two month.", verbose_level=3)
            db_manager.delete_job(job_id)
        else:
            vprint("Job will be kept.", verbose_level=3)
            kept_jobs.append(job_id)

    # Delete directorys locally
    vprint("Clean up directorys locally.", verbose_level=3)
    for directory in [INPUT_DIR, UPLOAD_DIR, OUTPUT_DIR]:
        for dir_name in os.listdir(directory):
            dir_path = os.path.join(directory, dir_name)
            if os.path.isdir(dir_path) and dir_name not in kept_jobs:
                shutil.rmtree(dir_path)

    # Delete work directorys on cluster
    vprint("Clean up directorys on cluster.", verbose_level=3)
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
    msg["From"] = SENDER_EMAIL
    msg["To"] = recipient
    msg["Subject"] = subject

    body = content
    msg.attach(MIMEText(body, "plain"))

    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(SMTP_USERNAME, SMTP_PASSWORD)
    server.sendmail(SENDER_EMAIL, recipient, msg.as_string())
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
        job = CosmopolitanJob(job_id=job_id)
    except JobNotFound:
        return render_template("html/errors/job_not_found_error.html", job_id=job_id)
    if not job.submitted:
        job.submit()
        send_submission_mail(job)
    else:
        job.check_status()

    if job.status == "RUNNING":
        reload_delay = 30
    else:
        reload_delay = None

    return render_template(
        "html/submission/submission.html", job=job, reload_delay=reload_delay
    )


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
def input_job():
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


@app.route("/clean_up")
def trigger_clean_up():
    clean_up()
    return "<h1>Putzen!</h1>"


@app.route("/results/<job_id>/<file_name>")
def result_file(job_id, file_name):
    """Serve result files."""
    vprint(f"Visiting /results/{job_id}/{file_name} to result_file()", verbose_level=1)
    try:
        output_dir = os.path.join(OUTPUT_DIR, job_id)
        return send_from_directory(output_dir, file_name)
    except NotFound:
        return render_template("html/errors/file_not_found.html")


if __name__ == "__main__":
    app.run()
