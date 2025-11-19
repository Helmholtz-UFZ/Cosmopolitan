"""CRNS Database Administration page for managing measurement updates."""

from datetime import datetime

import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html, register_page

from cosmopolitan_app.background_job_manager import get_background_job_manager
from cosmopolitan_app.constants import (
    CRNS_ADMIN_DUMMY_ID,
    CRNS_ADMIN_END_DATE_ID,
    CRNS_ADMIN_FAILED_COUNT_ID,
    CRNS_ADMIN_LAST_RUN_INFO_ID,
    CRNS_ADMIN_LOGS_TABLE_ID,
    CRNS_ADMIN_PURGE_BTN_ID,
    CRNS_ADMIN_PURGE_MODAL_CANCEL_ID,
    CRNS_ADMIN_PURGE_MODAL_CONFIRM_ID,
    CRNS_ADMIN_PURGE_MODAL_ID,
    CRNS_ADMIN_REFRESH_BTN_ID,
    CRNS_ADMIN_SAVE_CONFIG_BTN_ID,
    CRNS_ADMIN_START_DATE_ID,
    CRNS_ADMIN_START_UPDATE_BTN_ID,
    CRNS_ADMIN_STATUS_ALERT_ID,
    LOADING_OVERLAY_ID,
)
from cosmopolitan_app.layouts import create_header, page_container_column_layout
from cosmopolitan_app.logs_table import format_logs_list
from cosmopolitan_app.postgres_manager import PostgresManager

register_page(__name__, path="/crns-admin", title="CRNS Database Admin")


def create_config_section() -> dbc.Row:
    """Create the date configuration section."""
    return dbc.Row(
        dbc.Col(
            [
                html.H4("Date Configuration", className="mb-2"),
                html.P(
                    "Configure the date range for CRNS measurement updates. "
                    "Leave end date empty to always update up to yesterday.",
                    className="text-muted",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("Start Date"),
                                dbc.Input(
                                    id=CRNS_ADMIN_START_DATE_ID,
                                    type="date",
                                    placeholder="Select start date",
                                    className="mb-2",
                                ),
                            ],
                            md=4,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("End Date (optional)"),
                                dbc.Input(
                                    id=CRNS_ADMIN_END_DATE_ID,
                                    type="date",
                                    placeholder="Yesterday (default)",
                                    className="mb-2",
                                ),
                            ],
                            md=4,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("\u00a0"),  # Non-breaking space for alignment
                                dbc.Button(
                                    "Save Configuration",
                                    id=CRNS_ADMIN_SAVE_CONFIG_BTN_ID,
                                    color="primary",
                                    className="d-block",
                                ),
                            ],
                            md=4,
                        ),
                    ],
                    className="mb-3",
                ),
            ],
            className="m-2",
        )
    )


def create_actions_section() -> dbc.Row:
    """Create the actions section with update and purge buttons."""
    return dbc.Row(
        dbc.Col(
            [
                html.H4("Actions", className="mb-2"),
                html.P(
                    "Trigger database operations manually.",
                    className="text-muted",
                ),
                dbc.ButtonGroup(
                    [
                        dbc.Button(
                            [html.I(className="bi bi-play-fill me-1"), "Start Update"],
                            id=CRNS_ADMIN_START_UPDATE_BTN_ID,
                            color="success",
                            className="me-2",
                        ),
                        dbc.Button(
                            [html.I(className="bi bi-trash me-1"), "Purge Database"],
                            id=CRNS_ADMIN_PURGE_BTN_ID,
                            color="danger",
                        ),
                    ]
                ),
            ],
            className="m-2",
        )
    )


def create_status_section() -> dbc.Row:
    """Create the status information section."""
    return dbc.Row(
        dbc.Col(
            [
                html.H4("Status", className="mb-2"),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Card(
                                    dbc.CardBody(
                                        [
                                            html.H5(
                                                "Failed Updates", className="card-title"
                                            ),
                                            html.P(
                                                id=CRNS_ADMIN_FAILED_COUNT_ID,
                                                className="card-text display-6",
                                            ),
                                        ]
                                    ),
                                    className="mb-3",
                                ),
                            ],
                            md=4,
                        ),
                        dbc.Col(
                            [
                                dbc.Card(
                                    dbc.CardBody(
                                        [
                                            html.H5(
                                                "Latest Update Run",
                                                className="card-title",
                                            ),
                                            html.Div(id=CRNS_ADMIN_LAST_RUN_INFO_ID),
                                        ]
                                    ),
                                    className="mb-3",
                                ),
                            ],
                            md=8,
                        ),
                    ]
                ),
            ],
            className="m-2",
        )
    )


def create_logs_section() -> dbc.Row:
    """Create the logs display section."""
    return dbc.Row(
        dbc.Col(
            [
                html.H4("Latest Update Logs", className="mb-2"),
                html.P(
                    "Logs from the most recent update task run.",
                    className="text-muted",
                ),
                html.Div(
                    id=CRNS_ADMIN_LOGS_TABLE_ID,
                    children="No logs available.",
                    className="border p-3 bg-light rounded",
                    style={"maxHeight": "50vh", "overflowY": "auto"},
                ),
            ],
            className="m-2",
        )
    )


def create_purge_modal() -> dbc.Modal:
    """Create the confirmation modal for database purge."""
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Confirm Database Purge")),
            dbc.ModalBody(
                [
                    html.P(
                        "This will permanently delete ALL CRNS measurements "
                        "and reset the update history.",
                        className="text-danger fw-bold",
                    ),
                    html.P("This action cannot be undone. Are you sure?"),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button(
                        "Cancel",
                        id=CRNS_ADMIN_PURGE_MODAL_CANCEL_ID,
                        color="secondary",
                    ),
                    dbc.Button(
                        "Purge Database",
                        id=CRNS_ADMIN_PURGE_MODAL_CONFIRM_ID,
                        color="danger",
                    ),
                ]
            ),
        ],
        id=CRNS_ADMIN_PURGE_MODAL_ID,
        is_open=False,
    )


layout = page_container_column_layout(
    [
        create_header(
            "CRNS Database Administration",
            "Manage measurement database updates and configuration",
            "bg-info",
        ),
        dcc.Store(id=CRNS_ADMIN_DUMMY_ID, data=None),
        dbc.Alert(
            id=CRNS_ADMIN_STATUS_ALERT_ID,
            is_open=False,
            duration=5000,
            dismissable=True,
            className="m-2",
        ),
        dbc.Row(
            dbc.Col(
                dbc.Button(
                    [html.I(className="bi bi-arrow-clockwise me-1"), "Refresh"],
                    id=CRNS_ADMIN_REFRESH_BTN_ID,
                    color="secondary",
                ),
                className="m-2",
            )
        ),
        create_config_section(),
        html.Hr(),
        create_actions_section(),
        html.Hr(),
        create_status_section(),
        html.Hr(),
        create_logs_section(),
        create_purge_modal(),
    ]
)


@callback(
    Output(CRNS_ADMIN_STATUS_ALERT_ID, "children", allow_duplicate=True),
    Output(CRNS_ADMIN_STATUS_ALERT_ID, "color", allow_duplicate=True),
    Output(CRNS_ADMIN_STATUS_ALERT_ID, "is_open", allow_duplicate=True),
    Input(CRNS_ADMIN_SAVE_CONFIG_BTN_ID, "n_clicks"),
    State(CRNS_ADMIN_START_DATE_ID, "value"),
    State(CRNS_ADMIN_END_DATE_ID, "value"),
    prevent_initial_call=True,
)
def save_configuration(n_clicks, start_date_str, end_date_str):
    """Save the date configuration to the database."""
    if not n_clicks:
        return "", "info", False

    # Parse dates
    start_date = None
    end_date = None

    if start_date_str:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    if end_date_str:
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

    # Validate dates
    if start_date and end_date and start_date > end_date:
        return "Start date must be before end date.", "danger", True

    # Save to database
    PostgresManager.set_crns_date_range(start_date, end_date)

    return "Configuration saved successfully.", "success", True


@callback(
    Output(CRNS_ADMIN_STATUS_ALERT_ID, "children", allow_duplicate=True),
    Output(CRNS_ADMIN_STATUS_ALERT_ID, "color", allow_duplicate=True),
    Output(CRNS_ADMIN_STATUS_ALERT_ID, "is_open", allow_duplicate=True),
    Input(CRNS_ADMIN_START_UPDATE_BTN_ID, "n_clicks"),
    prevent_initial_call=True,
)
def start_update(n_clicks):
    """Trigger the update_db Celery task."""
    if not n_clicks:
        return "", "info", False

    # Check if start_date is configured
    start_date, _ = PostgresManager.get_crns_date_range()
    if start_date is None:
        return (
            "Cannot start update: Start date not configured. "
            "Please set a start date first.",
            "warning",
            True,
        )

    # Submit task to Celery
    job_manager = get_background_job_manager()
    result = job_manager.update_db_task.apply_async(queue="maintenance")

    return (
        f"Update task submitted. Task ID: {result.id}",
        "success",
        True,
    )


@callback(
    Output(CRNS_ADMIN_PURGE_MODAL_ID, "is_open"),
    Input(CRNS_ADMIN_PURGE_BTN_ID, "n_clicks"),
    Input(CRNS_ADMIN_PURGE_MODAL_CANCEL_ID, "n_clicks"),
    Input(CRNS_ADMIN_PURGE_MODAL_CONFIRM_ID, "n_clicks"),
    State(CRNS_ADMIN_PURGE_MODAL_ID, "is_open"),
    prevent_initial_call=True,
)
def toggle_purge_modal(purge_click, cancel_click, confirm_click, is_open):
    """Toggle the purge confirmation modal."""
    return not is_open


@callback(
    Output(CRNS_ADMIN_STATUS_ALERT_ID, "children", allow_duplicate=True),
    Output(CRNS_ADMIN_STATUS_ALERT_ID, "color", allow_duplicate=True),
    Output(CRNS_ADMIN_STATUS_ALERT_ID, "is_open", allow_duplicate=True),
    Output(CRNS_ADMIN_FAILED_COUNT_ID, "children", allow_duplicate=True),
    Output(CRNS_ADMIN_LAST_RUN_INFO_ID, "children", allow_duplicate=True),
    Output(CRNS_ADMIN_LOGS_TABLE_ID, "children", allow_duplicate=True),
    Input(CRNS_ADMIN_PURGE_MODAL_CONFIRM_ID, "n_clicks"),
    prevent_initial_call=True,
)
def confirm_purge(n_clicks):
    """Execute the database purge after confirmation."""
    if not n_clicks:
        return "", "info", False, "0", "No data", []

    PostgresManager.purge_crns_data()

    # Return updated status
    failed_count = PostgresManager.get_failed_update_count()
    last_run = PostgresManager.get_latest_update_run()
    last_run_info = format_last_run_info(last_run)
    logs_data = get_logs_for_run(last_run)

    return (
        "Database purged successfully. All measurements and update history cleared.",
        "success",
        True,
        str(failed_count),
        last_run_info,
        logs_data,
    )


@callback(
    Output(LOADING_OVERLAY_ID, "is_open", allow_duplicate=True),
    Input(CRNS_ADMIN_REFRESH_BTN_ID, "n_clicks"),
    Input(CRNS_ADMIN_DUMMY_ID, "data"),
    prevent_initial_call=True,
)
def show_loading(*inputs):
    """Show loading overlay when refresh is triggered."""
    return any(inp is not None for inp in inputs)


@callback(
    Output(CRNS_ADMIN_FAILED_COUNT_ID, "children"),
    Output(CRNS_ADMIN_LAST_RUN_INFO_ID, "children"),
    Output(CRNS_ADMIN_LOGS_TABLE_ID, "children"),
    Output(CRNS_ADMIN_START_DATE_ID, "value"),
    Output(CRNS_ADMIN_END_DATE_ID, "value"),
    Output(LOADING_OVERLAY_ID, "is_open", allow_duplicate=True),
    Input(CRNS_ADMIN_REFRESH_BTN_ID, "n_clicks"),
    prevent_initial_call="initial_duplicate",
)
def refresh_status(n_clicks):
    """Refresh status information, config, and logs on button click or initial load."""
    failed_count = PostgresManager.get_failed_update_count()
    last_run = PostgresManager.get_latest_update_run()
    last_run_info = format_last_run_info(last_run)
    logs_data = get_logs_for_run(last_run)

    # Load current config
    start_date, end_date = PostgresManager.get_crns_date_range()
    start_date_str = start_date.isoformat() if start_date else ""
    end_date_str = end_date.isoformat() if end_date else ""

    return (
        str(failed_count),
        last_run_info,
        logs_data,
        start_date_str,
        end_date_str,
        False,
    )


def format_last_run_info(run: dict | None) -> list:
    """Format the last run information for display."""
    if not run:
        return [html.P("No update runs recorded yet.", className="text-muted")]

    start_time = (
        run["start_time"].strftime("%Y-%m-%d %H:%M:%S") if run["start_time"] else "N/A"
    )
    end_time = (
        run["end_time"].strftime("%Y-%m-%d %H:%M:%S")
        if run["end_time"]
        else "Running..."
    )
    status = run["status"]
    pid = run["pid"]

    status_color = {
        "running": "primary",
        "completed": "success",
        "failed": "danger",
    }.get(status, "secondary")

    return [
        html.P([html.Strong("Start: "), start_time]),
        html.P([html.Strong("End: "), end_time]),
        html.P([html.Strong("PID: "), str(pid)]),
        html.P(
            [html.Strong("Status: "), dbc.Badge(status.upper(), color=status_color)]
        ),
    ]


def get_logs_for_run(run: dict | None):
    """Get logs for a specific update run based on PID and time range."""
    if not run:
        return "No logs available."

    pid = run["pid"]
    start_time = run["start_time"]
    end_time = run["end_time"] or datetime.now()

    # Query logs for this run - date must be string format
    logs = PostgresManager.query_logs(
        date=start_time.strftime("%Y-%m-%d"),
        sh=start_time.hour,
        sm=start_time.minute,
        eh=end_time.hour,
        em=end_time.minute,
        levels=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        pid=pid,
    )

    if not logs:
        return "No logs found for this update run."

    return format_logs_list(logs, show_tag=False, show_pid=False)
