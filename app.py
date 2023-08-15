"""Flask app that handles the Cosmopolitan Webserver."""

import os

from flask import Flask, render_template, request, redirect
from flask_wtf.csrf import CSRFProtect

from CosmopolitanJob import CosmopolitanJob, CosmopolitanJobForm, vprint

app = Flask(__name__)
csrf = CSRFProtect(app)

# CSRF key
app.config["SECRET_KEY"] = os.urandom(32)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 Mb limit


@app.route("/")
def hello_geek():
    """Hello world."""
    return "<h1>Hello from Flask & Docker</h1>"


@app.route("/confirm", methods=["GET", "POST"])
def confirm():
    """Confirm input and submit."""
    return "<h1>All input was valid</h1>"


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
        vprint(form.indep_var_files.data)
        if form.validate_on_submit():
            vprint(form.data)
            form.process()
            vprint(form.data)
            job = CosmopolitanJob(form=form)
            # job.save()
            return redirect("/confirm")
        vprint(form.selected_indep_var_files)
    return render_template("html/input/input.html", form=form)


@app.route("/privacy")
def privacy():
    """Return privacy notes."""
    # TODO
    return render_template("html/content/privacy.html")


if __name__ == "__main__":
    app.run()
