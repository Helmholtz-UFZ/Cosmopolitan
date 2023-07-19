"""Flask app that handles the Cosmopolitan Webserver."""

import os

from flask import Flask, render_template, request
from flask_wtf.csrf import CSRFProtect

from CosmopolitanJob import CosmopolitanJob
from CosmopolitanJob import CosmopolitanJobForm
app = Flask(__name__)
csrf = CSRFProtect(app)

# CSRF key
app.config["SECRET_KEY"] = os.urandom(32)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024    # 50 Mb limit


@app.route("/")
def hello_geek():
    """Hello world."""
    return "<h1>Hello from Flask & Docker</h2>"


@app.route("/input", methods=["GET", "POST"])
def input():
    """Input site for the job."""
    # Make new job and form if empty request form
    if len(request.form) == 0:
        job = CosmopolitanJob()
        form = job.form
        print(job.input)
    # If form was submitted validate
    else:
        form = CosmopolitanJobForm()
        if form.validate_on_submit():
            form.upload_file()
    return render_template("html/input/input.html", form=form)


@app.route("/privacy")
def privacy():
    """Return privacy notes."""
    # TODO
    return render_template("html/content/privacy.html")


if __name__ == "__main__":
    app.run()
