"""Flask app that handles the Cosmopolitan Webserver."""

import os

from flask import Flask, render_template, request, redirect
from flask_wtf.csrf import CSRFProtect

from cosmopolitan_job import CosmopolitanJob, CosmopolitanJobForm, vprint

app = Flask(__name__)
csrf = CSRFProtect(app)

# CSRF key
app.config["SECRET_KEY"] = os.urandom(32)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 Mb limit


@app.route("/")
def hello_geek():
    """Hello world."""
    return "<h1>Hello from Flask & Docker</h1>"


@app.route("/confirm/<job_id>", methods=["GET", "POST"])
def confirm(job_id):
    """Confirm input and submit."""
    job = CosmopolitanJob(job_id=job_id)
    return render_template("html/confirm/confirm.html", job=job)


@app.route("/input", methods=["GET", "POST"])
def input():
    """Input site for the job."""
    # Make new job and form if empty request form
    if len(request.form) == 0:
        job = CosmopolitanJob()
        form = job.form
    # If form was submitted validate
    else:
        form = CosmopolitanJobForm(new=False)
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
