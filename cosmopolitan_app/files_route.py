"""Serve static files from a directory."""

import logging

from flask import send_from_directory


def serve_files(app):
    """Serve static files from a directory."""

    @app.server.route("/pictures/<job_id>/<path:filename>")
    def serve_file(job_id, filename):
        """Serve pictures."""
        logging.debug(
            f"Serve picture {filename} for {job_id}", extra={"tag": "frontend"}
        )

        response = send_from_directory(f"work_dir/{job_id}", filename)

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
