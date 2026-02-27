"""Serve files from a directory."""

import io
import logging
import os
import zipfile

import dash_bootstrap_components as dbc
from flask import send_file, send_from_directory

from cosmopolitan_app.job import Job

log = logging.getLogger(__name__)

DOWNLOAD_ROUTE_TEMPLATE = "/download/<job_id>.zip"


def _download_href(job_id):
    """Build the download URL for a given job ID."""
    return DOWNLOAD_ROUTE_TEMPLATE.replace("<job_id>", str(job_id))


def create_download_button(job_id, class_name="w-100 mt-2"):
    """Create a download button for a job's work directory."""
    return dbc.Button(
        "Download work_dir",
        color="primary",
        href=_download_href(job_id),
        external_link=True,
        className=class_name,
    )


def serve_files(app):
    """Serve static files from a directory."""

    @app.server.route("/pictures/<job_id>/<path:filename>")
    def serve_file(job_id, filename):
        """Serve pictures."""
        log.debug(f"Serve picture {filename} for {job_id}", extra={"tag": "frontend"})
        # Assure that the job exists and all files are ready
        Job(job_id)

        # Dont use job.working_dir as from send_from_directory: The directory that
        # ``path`` must be located under, relative to the current application's root
        # path
        response = send_from_directory(f"work_dir/{job_id}", filename)

        # Add cache control headers to prevent browser caching
        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, max-age=0"
        )
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

        return response

    @app.server.route(DOWNLOAD_ROUTE_TEMPLATE)
    def download_work_dir(job_id):
        """Download the entire work directory as a zip file.

        Security: job_id is validated via Job() which calls validate_job_id()
        (format check) and queries the database (existence check). The working
        directory path is taken from the validated job object, never from user input.
        """
        log.info(f"Download work dir for {job_id}", extra={"tag": "frontend"})
        job = Job(job_id)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for root, _dirs, files in os.walk(job.working_dir):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    arcname = os.path.relpath(file_path, job.working_dir)
                    zip_file.write(file_path, arcname)

        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"{job_id}.zip",
        )
