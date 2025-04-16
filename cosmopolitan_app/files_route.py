"""Serve static files from a directory."""

import logging

from flask import send_from_directory

from cosmopolitan_app.job import Job


def serve_files(app):
    """Serve static files from a directory."""

    @app.server.route("/pictures/<job_id>/<path:filename>")
    def serve_file(job_id, filename):
        """Serve pictures."""
        logging.debug(f"Serve picture {filename} for {job_id}")
        job = Job(job_id)

        response = send_from_directory(f"work_dir/{job.job_id}", filename)

        # Add cache control headers to prevent browser caching
        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, max-age=0"
        )
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

        return response
