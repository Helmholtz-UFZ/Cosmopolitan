"""Dash form for the cosmopolitan job."""

import dash
import dash_bootstrap_components as dbc

# from dash import Input, Output, html
from dash import html

#
# from cosmopolitan_app.error_handling import create_callback_with_error_handling
# from cosmopolitan_app.job import Job
from cosmopolitan_app.layouts import create_header

# from cosmopolitan_app.postgres_manager import JobNotFound
#
dash.register_page(__name__)

header = create_header(
    "Submission",
    "foobar",
)

layout = [
    html.Div(header, id="header-id"),
    dbc.Row(
        dbc.Col(
            "Test",
            className="col-11 col-xl-8 mx-auto",
        )
    ),
]
#
#
# @create_callback_with_error_handling(
#     Output("header_id", "children"),
#     Input("url", "pathname"),
#     Input("initial-trigger", "id"),
# )
# def init_submission(pathname, _):
#     """Init the submission site."""
#     if pathname.startswith("/submission/"):
#         job_id = pathname.split("/submission/")[1]
#         job = Job(job_id)
#         return create_header("Submision", job.job_id, bg_color=job.status)
#     else:
#         raise JobNotFound
