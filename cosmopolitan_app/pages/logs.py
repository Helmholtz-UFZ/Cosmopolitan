"""View and filter application logs for debugging and monitoring.

This page provides access to the application's logging system, allowing you to track
system activity, debug issues, and monitor operations. You can:

- Filter logs by date and time range
- Select specific log levels (Debug, Info, Warning, Error, Critical)
- Filter by functional area using tags (job_submission, database, frontend, etc.)
- Filter by process ID to track specific worker or server processes
- View logs in a formatted, readable table
- Refresh logs on demand to see latest entries

Logs are stored in the database and include timestamps, log levels, logger names,
messages, and optional tags categorizing the log by system component. This is the
primary tool for understanding system behavior, diagnosing problems, and monitoring
background job execution.

NOTE: This docstring is displayed on the documentation webpage.
"""

import datetime

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback, dcc, html

from cosmopolitan_app.constants import (
    DATE_RANGE_DATEPICKER_LOGS_ID,
    END_HOUR_INPUT_LOGS_ID,
    END_MINUTE_INPUT_LOGS_ID,
    LOG_LEVELS_DROPDOWN_LOGS_ID,
    LOG_OUTPUT_DIV_LOGS_ID,
    LOG_TAGS_DROPDOWN_LOGS_ID,
    PID_INPUT_LOGS_ID,
    PID_RADIO_CHECKLIST_LOGS_ID,
    START_HOUR_INPUT_LOGS_ID,
    START_MINUTE_INPUT_LOGS_ID,
    TIME_ERROR_DIV_LOGS_ID,
    TIME_INPUT_GROUP_LOGS_ID,
)
from cosmopolitan_app.layouts import create_header, page_container_column_layout
from cosmopolitan_app.logger import log_categories
from cosmopolitan_app.logs_table import format_logs_list
from cosmopolitan_app.postgres_manager import PostgresManager

dash.register_page(
    __name__,
    path_template="/logs",
)


def layout():
    """Dynamic layout that calculates current time on each page visit."""
    # Calculate time values dynamically
    now = datetime.datetime.now()
    start_hour = now.hour - 1 if now.hour > 0 else 23
    start_minute = now.minute
    end_hour = now.hour
    end_minute = now.minute

    header = create_header(
        "View logs", "Show logs of the webserver", bg_color="bg-info"
    )

    # UI Components
    date_selector = [
        html.Label("Select Date Range"),
        html.Br(),
        dcc.DatePickerSingle(
            id=DATE_RANGE_DATEPICKER_LOGS_ID,
            date=now.date(),
        ),
    ]

    time_selector = [
        html.Label("Time Range"),
        html.Div(
            children=[
                dbc.InputGroup(
                    [
                        dbc.InputGroupText("From"),
                        dbc.Input(
                            id=START_HOUR_INPUT_LOGS_ID,
                            type="number",
                            value=start_hour,
                            min=0,
                            max=23,
                        ),
                        dbc.InputGroupText(":"),
                        dbc.Input(
                            id=START_MINUTE_INPUT_LOGS_ID,
                            type="number",
                            value=start_minute,
                            min=0,
                            max=59,
                        ),
                        dbc.InputGroupText("To"),
                        dbc.Input(
                            id=END_HOUR_INPUT_LOGS_ID,
                            type="number",
                            value=end_hour,
                            min=0,
                            max=23,
                        ),
                        dbc.InputGroupText(":"),
                        dbc.Input(
                            id=END_MINUTE_INPUT_LOGS_ID,
                            type="number",
                            value=end_minute,
                            min=0,
                            max=59,
                        ),
                    ],
                    id=TIME_INPUT_GROUP_LOGS_ID,
                ),
                html.Small(id=TIME_ERROR_DIV_LOGS_ID, className="text-danger"),
            ],
        ),
    ]

    log_levels = [
        html.Label("Log Levels"),
        dcc.Dropdown(
            id=LOG_LEVELS_DROPDOWN_LOGS_ID,
            options=[
                {"label": "Debug", "value": "DEBUG"},
                {"label": "Info", "value": "INFO"},
                {"label": "Warning", "value": "WARNING"},
                {"label": "Error", "value": "ERROR"},
                {"label": "Critical", "value": "CRITICAL"},
            ],
            value=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            multi=True,
        ),
    ]

    available_tags = [tag for tags in log_categories.values() for tag in tags]
    tag_options = [
        {"label": tag.replace("_", " ").title(), "value": tag} for tag in available_tags
    ]
    tag_filter = [
        html.Label("Tag"),
        dcc.Dropdown(
            id=LOG_TAGS_DROPDOWN_LOGS_ID,
            options=tag_options,
            value=available_tags,
            multi=True,
        ),
    ]

    pid_selector = [
        html.Label("PID"),
        dbc.InputGroup(
            [
                dbc.InputGroupText(
                    dbc.Checklist(
                        id=PID_RADIO_CHECKLIST_LOGS_ID,
                        options=[{"label": "Select by PID", "value": "on"}],
                        value=[],
                        switch=True,
                    ),
                ),
                dbc.Input(
                    id=PID_INPUT_LOGS_ID,
                    type="number",
                    placeholder="Process ID",
                    disabled=True,
                ),
            ],
        ),
    ]

    page_layout = [
        header,
        dbc.Container(
            [
                dbc.Row(
                    [dbc.Col(date_selector, width=6), dbc.Col(time_selector, width=6)],
                    className="mb-4",
                ),
                dbc.Row(
                    [
                        dbc.Col(log_levels, width=4),
                        dbc.Col(tag_filter, width=4),
                        dbc.Col(pid_selector, width=4),
                    ],
                    className="mb-4",
                ),
                html.Div(
                    id=LOG_OUTPUT_DIV_LOGS_ID,
                    children="Logs will appear here...",
                    className="border p-3 bg-light rounded",
                    # no Bootstrap class for dynamic maxHeight + overflow scroll
                    style={"maxHeight": "70vh", "overflowY": "auto"},
                ),
            ],
            className="my-4",
        ),
    ]

    return page_container_column_layout(page_layout)


@callback(
    Output(LOG_OUTPUT_DIV_LOGS_ID, "children"),
    Output(PID_INPUT_LOGS_ID, "disabled"),
    Output(TIME_ERROR_DIV_LOGS_ID, "children"),
    Output(TIME_INPUT_GROUP_LOGS_ID, "className"),
    Input(DATE_RANGE_DATEPICKER_LOGS_ID, "date"),
    Input(START_HOUR_INPUT_LOGS_ID, "value"),
    Input(START_MINUTE_INPUT_LOGS_ID, "value"),
    Input(END_HOUR_INPUT_LOGS_ID, "value"),
    Input(END_MINUTE_INPUT_LOGS_ID, "value"),
    Input(LOG_LEVELS_DROPDOWN_LOGS_ID, "value"),
    Input(LOG_TAGS_DROPDOWN_LOGS_ID, "value"),
    Input(PID_RADIO_CHECKLIST_LOGS_ID, "value"),
    Input(PID_INPUT_LOGS_ID, "value"),
)
def log_manager(date, sh, sm, eh, em, levels, tag, pid_radio, pid):
    """Manage and display logs based on user input."""
    if pid_radio != ["on"]:
        pid = "all"
    disabled_pid = pid_radio == ["on"]

    bad_values_log = "Select a valid time range."
    bad_input_group_class = "border border-danger rounded"
    if None in (sh, sm, eh, em):
        error_msg = "All time fields must be filled."
        return bad_values_log, disabled_pid, error_msg, bad_input_group_class

    if (sh, sm) >= (eh, em):
        error_msg = "Start time must be before end time."
        return bad_values_log, disabled_pid, error_msg, bad_input_group_class

    if pid == "all":
        pid = None
    logs = PostgresManager.query_logs(date, sh, sm, eh, em, levels, pid, tag)
    if not logs:
        return "No logs found for the selected criteria.", disabled_pid, "", ""

    log_formatted = format_logs_list(logs, show_tag=True, show_pid=True)

    return log_formatted, disabled_pid, "", ""
