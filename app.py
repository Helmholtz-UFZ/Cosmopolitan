"""Flask app that handles the Cosmopolitan Webserver."""

import os


import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import Flask, render_template, request, redirect, url_for
from flask_wtf.csrf import CSRFProtect

from cosmopolitan_job import CosmopolitanJob
from config import (
    vprint,
    SMTP_SERVER,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_PASSWORD,
    SENDER_EMAIL,
)
from cosmopolitan_job_form import CosmopolitanJobForm, json_load_4_jinja
from db_manager import JobNotFound

app = Flask(__name__)

csrf = CSRFProtect(app)

# CSRF key
app.config["SECRET_KEY"] = os.urandom(32)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500 Mb limit

app.jinja_env.globals.update(json_loads=json_load_4_jinja)


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
    with open("templates/emails/submission_email.txt", "r", encoding="UTF-8") as f_handle:
        content = f_handle.read().format(job_id=job.job_id, url=url)
    if job.email != "":
        send_mail(job.email, f'Job "{ job.job_id }" submitted', content)


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
        send_submission_mail(job)
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


if __name__ == "__main__":
    app.run()
