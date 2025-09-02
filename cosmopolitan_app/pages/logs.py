"""Logs Page for Cosmopolitan App."""

import datetime

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback, dcc, html

from cosmopolitan_app.layouts import create_header
from cosmopolitan_app.logger import log_categories
from cosmopolitan_app.postgres_manager import PostgresManager

dash.register_page(
    __name__,
    path_template="/logs",
)


def level_badge(level):
    """Format logs with color-coded levels."""
    color_map = {
        "DEBUG": "secondary",
        "INFO": "info",
        "WARNING": "warning",
        "ERROR": "danger",
        "CRITICAL": "dark",
    }
    return dbc.Badge(level, color=color_map.get(level, "primary"), className="me-1")


def tag_badge(tag):
    """Format logs with color-coded tags."""
    # Determine category for the tag
    for category, tags in log_categories.items():
        if tag in tags:
            break

    color_map = {
        "Core Areas": "primary",
        "User Areas": "success",
        "System Areas": "warning",
        "unknown": "secondary",
    }
    return dbc.Badge(tag.upper(), color=color_map[category], className="me-1")


def layout():
    """Layout for the logs page."""
    start_hour = datetime.datetime.now().hour - 1
    start_minute = datetime.datetime.now().minute
    end_hour = datetime.datetime.now().hour
    end_minute = datetime.datetime.now().minute

    header = create_header(
        "View logs", "Show logs of the webserver", bg_color="bg-info"
    )
    # UI Components
    date_selector = [
        html.Label("Select Date Range"),
        html.Br(),
        dcc.DatePickerSingle(
            id="log-date-range",
            date=datetime.date.today(),
        ),
    ]

    time_selector = [
        html.Label("Time Range"),
        html.Div(
            id="time-input-wrapper",
            children=[
                dbc.InputGroup(
                    [
                        dbc.InputGroupText("From"),
                        dbc.Input(
                            id="start-hour",
                            type="number",
                            value=start_hour,
                            min=0,
                            max=23,
                        ),
                        dbc.InputGroupText(":"),
                        dbc.Input(
                            id="start-minute",
                            type="number",
                            value=start_minute,
                            min=0,
                            max=59,
                        ),
                        dbc.InputGroupText("To"),
                        dbc.Input(
                            id="end-hour", type="number", value=end_hour, min=0, max=23
                        ),
                        dbc.InputGroupText(":"),
                        dbc.Input(
                            id="end-minute",
                            type="number",
                            value=end_minute,
                            min=0,
                            max=59,
                        ),
                    ],
                    id="time-input-group",
                ),
                html.Small(id="time-error", className="text-danger"),
            ],
        ),
    ]

    log_levels = [
        html.Label("Log Levels"),
        dcc.Dropdown(
            id="log-levels",
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
            id="log-tags",
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
                        id="pid-radio",
                        options=[{"label": "Select by PID", "value": "on"}],
                        value=[],
                        switch=True,
                    ),
                ),
                dbc.Input(
                    id="log-pid",
                    type="number",
                    placeholder="Process ID",
                    disabled=True,
                ),
            ],
        ),
    ]

    # App Layout
    return [
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
                    id="log-output",
                    children="Logs will appear here...",
                    className="border p-3 bg-light rounded",
                    style={"maxHeight": "70vh", "overflowY": "auto"},
                ),
            ],
            className="my-4",
        ),
    ]


@callback(
    Output("log-output", "children"),
    Output("log-pid", "disabled"),
    Output("time-error", "children"),
    Output("time-input-group", "className"),
    Input("log-date-range", "date"),
    Input("start-hour", "value"),
    Input("start-minute", "value"),
    Input("end-hour", "value"),
    Input("end-minute", "value"),
    Input("log-levels", "value"),
    Input("log-tags", "value"),
    Input("pid-radio", "value"),
    Input("log-pid", "value"),
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

    log_formatted = html.Ul(
        [
            html.Li(
                [
                    level_badge(log["level"]),
                    tag_badge(log["tag"]),
                    f" at {log['timestamp']} ",
                    f"in {log['module']} [PID {log['pid']}]:\n{log['message']}",
                ],
                style={"white-space": "pre-wrap"},
            )
            for log in logs
        ]
    )

    return log_formatted, disabled_pid, "", ""
