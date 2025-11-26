"""Serve files from a directory."""

import logging

from flask import send_from_directory

from cosmopolitan_app.job import Job


def serve_files(app):
    """Serve static files from a directory."""

    @app.server.route("/pictures/<job_id>/<path:filename>")
    def serve_file(job_id, filename):
        """Serve pictures."""
        logging.debug(
            f"Serve picture {filename} for {job_id}", extra={"tag": "frontend"}
        )
        # Assure that the job exists and all files are ready
        job = Job(job_id)

        response = send_from_directory(job.working_dir, filename)
        # Add cache control headers to prevent browser caching
        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, max-age=0"
        )
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

        return response

    # @app.route("/results/<job_id>/<file_name>")
    # def result_file(job_id, file_name):
    #     """Serve result files."""
    #     logging.info(
    #         f"Visiting /results/{job_id}/{file_name} to result_file()",
    #         extra={"tag": "frontend"},
    #     )
    #     download_path = os.path.join(*WEB_WORK_DIR.split(os.sep)[2:], job_id)
    #     safe_file_name = os.path.basename(file_name)
    #
    #     return send_from_directory(download_path, safe_file_name)
