"""Job Management Dashboard for Cosmopolitan App."""

import logging
from datetime import datetime

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dash_table

from cosmopolitan_app.job import Job
from cosmopolitan_app.layouts import create_header
from cosmopolitan_app.postgres_manager import PostgresManager
from cosmopolitan_app.utils import clean_up_jobs

dash.register_page(__name__)


table = dash_table.DataTable(
    id="jobs-table",
    columns=[
        {"id": "job_id", "name": "Job ID", "presentation": "markdown"},
        {"id": "status", "name": "Status"},
        {"id": "start_date", "name": "Start Date"},
        {"id": "submitted", "name": "Submitted"},
    ],
    data=[],
    row_selectable="multi",
    selected_rows=[],
    style_cell={"textAlign": "center"},
    cell_selectable=False,
    style_data_conditional=[
        {
            "if": {
                "column_id": "job_id",
            },
            "textAlign": "left",
            "fontFamily": "monospace",
        },
        {
            "if": {
                "filter_query": '{status} = "COMPLETED"',
                "column_id": "status",
            },
            "backgroundColor": "#3498db",
        },
        {
            "if": {
                "filter_query": '{status} = "RUNNING"',
                "column_id": "status",
            },
            "backgroundColor": "#2ecc71",
        },
        {
            "if": {
                "filter_query": '{status} = "FAILED"',
                "column_id": "status",
            },
            "backgroundColor": "#e74c3c",
        },
        {
            "if": {
                "filter_query": '{status} = "PENDING"',
                "column_id": "status",
            },
            "backgroundColor": "#f39c12",
        },
    ],
)

button_group = [
    dbc.Button(
        "Refresh Jobs",
        id="refresh_btn",
        color="primary",
        className="ms-2 float-end",
    ),
    dbc.Button(
        "Delete Selection",
        id="delete_btn",
        color="danger",
        className="ms-2 float-end",
    ),
    dbc.Button(
        "Clean",
        id="clean_btn",
        color="warning",
        className="ms-2 float-end",
    ),
]

layout = [
    create_header(
        "Job Management",
        "Overview and management of jobs in the Cosmopolitan App",
        bg_color="bg-info",
    ),
    dbc.Row(
        dbc.Col(
            button_group,
        ),
        className="m-2",
    ),
    dbc.Row(
        dbc.Col(
            table,
        ),
        className="m-2",
    ),
]


@callback(
    Output("jobs-table", "data"),
    [
        Input("delete_btn", "n_clicks"),
        Input("clean_btn", "n_clicks"),
        Input("refresh_btn", "n_clicks"),
    ],
    [State("jobs-table", "selected_rows"), State("jobs-table", "data")],
    prevent_initial_call=False,
)
def job_mangament_dashboard(
    delete_clicks, clean_clicks, refresh_clicks, selected_rows, table_data
):
    """Manage job actions in the dashboard."""
    logging.info("Job management dashboard callback triggered.")
    button_id = dash.callback_context.triggered[0]["prop_id"].split(".")[0]

    if button_id == "delete_btn" and selected_rows:
        logging.info("Deleting selected jobs")
        logging.debug(f"Selected rows: {selected_rows}")
        selected_job_ids = [
            table_data[i]["job_id"].strip("[]").split("/")[1] for i in selected_rows
        ]
        for job_id in selected_job_ids:
            job = Job(job_id)
            job.delete()
    elif button_id == "clean_btn":
        logging.info("Cleaning unsubmitted jobs")
        clean_up_jobs(days_delete_not_submitted=0)

    jobs_dict = PostgresManager.list_jobs()

    rows = []
    submission_base_path = dash.page_registry["pages.submission"]["path_template"]
    for job_id, job_data in jobs_dict.items():
        start_date = (
            job_data["start_date"].strftime("%Y-%m-%d %H:%M:%S")
            if isinstance(job_data["start_date"], datetime)
            else job_data["start_date"]
        )

        job_id_link = submission_base_path.replace("<job_id>", job_id)
        job_id_markdown = f"[{job_id}]({job_id_link})"

        rows.append(
            {
                "job_id": job_id_markdown,
                "status": job_data["status"],
                "start_date": start_date,
                "submitted": "Yes" if job_data["submitted"] else "No",
            }
        )

    return rows
