"""Monitor and manage background workers and tasks.

This administrative page provides real-time visibility into the Celery background task
system that processes prediction jobs and maintenance operations. Features include:

**Worker Status:**
- View active worker processes and their configuration
- See worker pool types, concurrency settings, and queue assignments
- Check worker availability and health

**Task Monitoring:**
- View currently executing tasks (active tasks)
- See tasks waiting in worker queues (reserved tasks)
- Monitor scheduled tasks waiting for their run time
- Track revoked (cancelled) tasks
- Display task details including name, arguments, and execution time

**Task Control:**
- Kill actively running tasks (forcefully terminate)
- Cancel scheduled tasks before they execute
- Confirmation dialogs prevent accidental terminations

**Status Updates:**
- Manual refresh to get latest worker and task information
- Timestamp showing when data was last refreshed

This page is essential for monitoring system load, debugging stuck tasks, and managing
resource usage during peak periods.

NOTE: This docstring is displayed on the documentation webpage.
"""

import logging
from datetime import datetime

import dash
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html

from cosmopolitan_app.background_job_manager import background_job_manager
from cosmopolitan_app.constants import (
    ACTIVE_TASKS_TABLE_WORKER_MANAGEMENT_ID,
    CANCEL_BUTTON_WORKER_MANAGEMENT_ID,
    CANCEL_MODAL_CANCEL_BUTTON_WORKER_MANAGEMENT_ID,
    CANCEL_MODAL_CONFIRM_BUTTON_WORKER_MANAGEMENT_ID,
    CANCEL_MODAL_TASK_INFO_DIV_WORKER_MANAGEMENT_ID,
    CANCEL_MODAL_WORKER_MANAGEMENT_ID,
    DUMMY_DIV_WORKER_MANAGEMENT_ID,
    KILL_BUTTON_WORKER_MANAGEMENT_ID,
    KILL_MODAL_CANCEL_BUTTON_WORKER_MANAGEMENT_ID,
    KILL_MODAL_CONFIRM_BUTTON_WORKER_MANAGEMENT_ID,
    KILL_MODAL_TASK_INFO_DIV_WORKER_MANAGEMENT_ID,
    KILL_MODAL_WORKER_MANAGEMENT_ID,
    LAST_REFRESH_DIV_WORKER_MANAGEMENT_ID,
    LOADING_OVERLAY_MODAL_SHARED_ID,
    REFRESH_BUTTON_WORKER_MANAGEMENT_ID,
    RESERVED_TASKS_TABLE_WORKER_MANAGEMENT_ID,
    REVOKED_TASKS_TABLE_WORKER_MANAGEMENT_ID,
    SCHEDULED_TASKS_TABLE_WORKER_MANAGEMENT_ID,
    STATS_CARD_DIV_WORKER_MANAGEMENT_ID,
)
from cosmopolitan_app.error_handling import WorkerNotAvailableError
from cosmopolitan_app.layouts import create_header, page_container_column_layout

log = logging.getLogger(__name__)

# Register the page
dash.register_page(__name__, path="/worker_management")


# Factory functions for layout components
def create_task_datatable(
    table_id: str, columns: list, row_selectable: str | bool = False
) -> dag.AgGrid:
    """Create an AgGrid with common styling for task display.

    Args:
        table_id: Component ID for the table
        columns: List of column definitions (DataTable format, converted internally)
        row_selectable: "single", "multi", or False

    Returns:
        dag.AgGrid with common styling applied
    """
    column_defs = []
    for col in columns:
        col_def = {"field": col["id"], "headerName": col["name"]}
        if col["id"] == "task_id":
            col_def["cellStyle"] = {"fontFamily": "monospace", "fontSize": "12px"}
        column_defs.append(col_def)

    grid_options = {
        "pagination": True,
        "paginationPageSize": 10,
    }

    if row_selectable:
        mode = "multiRow" if row_selectable == "multi" else "singleRow"
        grid_options["rowSelection"] = {"mode": mode}

    return dag.AgGrid(
        id=table_id,
        columnDefs=column_defs,
        rowData=[],
        defaultColDef={
            "cellStyle": {"textAlign": "left", "padding": "8px"},
            "sortable": True,
            "resizable": True,
        },
        dashGridOptions=grid_options,
        getRowStyle={
            "styleConditions": [
                {
                    "condition": "params.node.rowIndex % 2 !== 0",
                    "style": {"backgroundColor": "#f8f9fa"},
                },
            ],
        },
        columnSize="responsiveSizeToFit",
    )


def create_task_section(
    title: str,
    description: str,
    table_component,
    button=None,
) -> dbc.Row:
    """Create a task section with consistent layout.

    Args:
        title: Section heading
        description: Muted description text
        table_component: The DataTable component
        button: Optional button component

    Returns:
        dbc.Row containing the section
    """
    children = [
        html.H4(title, className="mb-2"),
        html.P(description, className="text-muted"),
        table_component,
    ]
    if button:
        children.append(button)

    return dbc.Row(dbc.Col(children, className="m-2"))


# Helper functions for data formatting
def format_duration(start_timestamp: float) -> str:
    """Convert timestamp to human-readable duration.

    Args:
        start_timestamp: Unix timestamp when task started

    Returns:
        str: Formatted duration (e.g., "2m 30s", "1h 15m")
    """
    if not start_timestamp:
        return "N/A"

    duration = datetime.now().timestamp() - start_timestamp
    hours = int(duration // 3600)
    minutes = int((duration % 3600) // 60)
    seconds = int(duration % 60)

    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


def count_tasks_for_worker(task_list, worker_name):
    """Count tasks assigned to a specific worker."""
    return sum(
        1 for t in task_list if isinstance(t, dict) and t["worker"] == worker_name
    )


def extract_job_id_from_task(task: dict) -> str:
    """Extract job_id from task if it's a computation task.

    Args:
        task: Task dictionary with args field

    Returns:
        str: Job ID or empty string if not a computation task
    """
    task_name = task["name"]
    if "computation" in task_name and task.get(
        "args"
    ):  # args may be empty/absent for non-computation tasks
        # Computation tasks have job_id as first argument
        try:
            return task["args"][0] if task["args"] else ""
        except (IndexError, KeyError):
            return ""
    return ""


def format_active_tasks(active_list: list) -> list:
    """Format active tasks for DataTable display.

    Args:
        active_list: List of active tasks with worker field

    Returns:
        list: List of task dictionaries formatted for table
    """
    tasks = []
    for task in active_list:
        tasks.append(
            {
                "task_id": task["id"],
                "task_name": task["name"].split(".")[-1],
                "full_name": task["name"],
                "worker": task["worker"],
                "start_time": (
                    datetime.fromtimestamp(task["time_start"]).strftime("%H:%M:%S")
                    if task.get(
                        "time_start"
                    )  # time_start absent for tasks not yet started
                    else "N/A"
                ),
                "duration": format_duration(task.get("time_start")),  # see above
                "job_id": extract_job_id_from_task(task),
            }
        )
    return tasks


def format_reserved_tasks(reserved_list: list) -> list:
    """Format reserved tasks for DataTable display.

    Args:
        reserved_list: List of reserved tasks with worker field

    Returns:
        list: List of task dictionaries formatted for table
    """
    tasks = []
    for task in reserved_list:
        tasks.append(
            {
                "task_id": task["id"],
                "task_name": task["name"].split(".")[-1],
                "full_name": task["name"],
                # delivery_info may be absent for tasks without routing info
                "queue": task.get("delivery_info", {}).get("routing_key", "default"),
                "worker": task["worker"],
            }
        )
    return tasks


def format_scheduled_tasks(scheduled_list: list) -> list:
    """Format scheduled tasks for DataTable display.

    Args:
        scheduled_list: List of scheduled tasks with worker field

    Returns:
        list: List of task dictionaries formatted for table
    """
    tasks = []
    for task in scheduled_list:
        eta = task.get("eta")  # eta absent for tasks without scheduled time
        eta_str = (
            datetime.fromisoformat(eta).strftime("%Y-%m-%d %H:%M:%S") if eta else "N/A"
        )
        tasks.append(
            {
                "task_id": task["id"],
                "task_name": task["name"].split(".")[-1],
                "full_name": task["name"],
                "eta": eta_str,
                # delivery_info may be absent for tasks without routing info
                "queue": task.get("delivery_info", {}).get("routing_key", "default"),
                "worker": task["worker"],
            }
        )
    return tasks


def format_revoked_tasks(revoked_list: list) -> list:
    """Format revoked tasks for DataTable display with enrichment from result backend.

    Args:
        revoked_list: List of revoked tasks with id and worker fields

    Returns:
        list: List of task dictionaries formatted for table
    """
    tasks = []
    for task in revoked_list:
        task_id = task["id"]
        worker = task["worker"]

        # Enrich with info from result backend
        result_info = background_job_manager.get_task_result_info(task_id)

        tasks.append(
            {
                "task_id": task_id,
                "task_name": result_info["task_name"],
                "worker": worker,
                "status": result_info["status"],
            }
        )
    return tasks


def format_worker_stats(overview: dict) -> list:
    """Format worker statistics into cards.

    Args:
        overview: Task overview with active, reserved, scheduled (flat lists with worker
        field)

    Returns:
        list: List of card components showing worker stats
    """
    # Get list of online workers from overview
    all_workers = set(overview["workers"])

    if not all_workers:
        raise WorkerNotAvailableError("No workers currently running")

    # Count tasks per worker

    cards = []
    for worker in sorted(all_workers):
        active_count = count_tasks_for_worker(overview["active"], worker)
        reserved_count = count_tasks_for_worker(overview["reserved"], worker)
        scheduled_count = count_tasks_for_worker(overview["scheduled"], worker)

        card = dbc.Card(
            [
                dbc.CardHeader(html.H5(worker, className="mb-0")),
                dbc.CardBody(
                    [
                        html.P(
                            [
                                html.Strong("Active: "),
                                f"{active_count} ",
                                html.Strong("Reserved: "),
                                f"{reserved_count} ",
                                html.Strong("Scheduled: "),
                                f"{scheduled_count}",
                            ],
                            className="mb-0",
                        ),
                    ]
                ),
            ],
            className="mb-2",
        )
        cards.append(card)

    return cards


# Layout
layout = page_container_column_layout(
    [
        create_header(
            "Worker Management",
            "Monitor and manage Celery workers and tasks",
            "bg-info",
        ),
        # Controls Section (at top)
        dbc.Row(
            dbc.Col(
                [
                    dbc.Button(
                        [html.I(className="bi bi-arrow-clockwise me-1"), "Refresh"],
                        id=REFRESH_BUTTON_WORKER_MANAGEMENT_ID,
                        color="primary",
                        className="me-3",
                    ),
                    html.Small(
                        id=LAST_REFRESH_DIV_WORKER_MANAGEMENT_ID,
                        children="Last refresh: --",
                        className="text-muted",
                    ),
                ],
                className="m-2",
            )
        ),
        # Worker Status Section
        dbc.Row(
            dbc.Col(
                [
                    html.H4("Worker Status", className="mb-3"),
                    html.Div(
                        id=STATS_CARD_DIV_WORKER_MANAGEMENT_ID,
                        children=[
                            dbc.Alert("Loading worker information...", color="info")
                        ],
                    ),
                ],
                className="m-2",
            )
        ),
        # Active Tasks Section
        create_task_section(
            "Active Tasks",
            "Tasks currently being executed by workers",
            create_task_datatable(
                ACTIVE_TASKS_TABLE_WORKER_MANAGEMENT_ID,
                [
                    {"id": "task_id", "name": "Task ID"},
                    {"id": "task_name", "name": "Task Name"},
                    {"id": "worker", "name": "Worker"},
                    {"id": "start_time", "name": "Start Time"},
                    {"id": "duration", "name": "Duration"},
                    {"id": "job_id", "name": "Job ID"},
                ],
                row_selectable="single",
            ),
            dbc.Button(
                [html.I(className="bi bi-x-octagon-fill me-1"), "Kill Selected Task"],
                id=KILL_BUTTON_WORKER_MANAGEMENT_ID,
                color="danger",
                className="mt-2",
                disabled=True,
            ),
        ),
        # Reserved Tasks Section
        create_task_section(
            "Reserved Tasks",
            "Tasks claimed by workers but not yet started",
            create_task_datatable(
                RESERVED_TASKS_TABLE_WORKER_MANAGEMENT_ID,
                [
                    {"id": "task_id", "name": "Task ID"},
                    {"id": "task_name", "name": "Task Name"},
                    {"id": "queue", "name": "Queue"},
                    {"id": "worker", "name": "Worker"},
                ],
                row_selectable="single",
            ),
        ),
        # Scheduled Tasks Section
        create_task_section(
            "Scheduled Tasks",
            "Tasks scheduled for future execution",
            create_task_datatable(
                SCHEDULED_TASKS_TABLE_WORKER_MANAGEMENT_ID,
                [
                    {"id": "task_id", "name": "Task ID"},
                    {"id": "task_name", "name": "Task Name"},
                    {"id": "eta", "name": "ETA"},
                    {"id": "queue", "name": "Queue"},
                ],
                row_selectable="single",
            ),
            dbc.Button(
                [html.I(className="bi bi-x-circle me-1"), "Cancel Selected Task"],
                id=CANCEL_BUTTON_WORKER_MANAGEMENT_ID,
                color="warning",
                className="mt-2",
                disabled=True,
            ),
        ),
        # Revoked Tasks Section
        create_task_section(
            "Revoked Tasks",
            "Tasks that have been cancelled",
            create_task_datatable(
                REVOKED_TASKS_TABLE_WORKER_MANAGEMENT_ID,
                [
                    {"id": "task_id", "name": "Task ID"},
                    {"id": "task_name", "name": "Task Name"},
                    {"id": "worker", "name": "Worker"},
                    {"id": "status", "name": "Status"},
                ],
            ),
        ),
        # Hidden components
        dcc.Store(id=DUMMY_DIV_WORKER_MANAGEMENT_ID, data=None),
        # Kill Confirmation Modal
        dbc.Modal(
            [
                dbc.ModalHeader("Confirm Task Termination"),
                dbc.ModalBody(
                    [
                        html.P(
                            "⚠️ WARNING: This will send SIGTERM to the worker process.",
                            className="text-danger fw-bold",
                        ),
                        html.P("The worker process will be killed immediately."),
                        html.Pre(
                            id=KILL_MODAL_TASK_INFO_DIV_WORKER_MANAGEMENT_ID,
                            className="bg-light p-2",
                        ),
                        html.P(
                            "Are you sure you want to KILL this task?",
                            className="fw-bold text-danger",
                        ),
                    ]
                ),
                dbc.ModalFooter(
                    [
                        dbc.Button(
                            [html.I(className="bi bi-x-circle me-1"), "Cancel"],
                            id=KILL_MODAL_CANCEL_BUTTON_WORKER_MANAGEMENT_ID,
                            color="secondary",
                        ),
                        dbc.Button(
                            [
                                html.I(className="bi bi-x-octagon-fill me-1"),
                                "Kill Task",
                            ],
                            id=KILL_MODAL_CONFIRM_BUTTON_WORKER_MANAGEMENT_ID,
                            color="danger",
                        ),
                    ]
                ),
            ],
            id=KILL_MODAL_WORKER_MANAGEMENT_ID,
            is_open=False,
        ),
        # Cancel Confirmation Modal
        dbc.Modal(
            [
                dbc.ModalHeader("Confirm Task Cancellation"),
                dbc.ModalBody(
                    [
                        html.P("This will prevent the task from executing."),
                        html.P(
                            "If the task is already running, it will continue until completion."  # noqa
                        ),
                        html.Pre(
                            id=CANCEL_MODAL_TASK_INFO_DIV_WORKER_MANAGEMENT_ID,
                            className="bg-light p-2",
                        ),
                        html.P(
                            "Are you sure you want to CANCEL this task?",
                            className="fw-bold",
                        ),
                    ]
                ),
                dbc.ModalFooter(
                    [
                        dbc.Button(
                            [html.I(className="bi bi-x-circle me-1"), "Cancel"],
                            id=CANCEL_MODAL_CANCEL_BUTTON_WORKER_MANAGEMENT_ID,
                            color="secondary",
                        ),
                        dbc.Button(
                            [html.I(className="bi bi-x-circle me-1"), "Cancel Task"],
                            id=CANCEL_MODAL_CONFIRM_BUTTON_WORKER_MANAGEMENT_ID,
                            color="warning",
                        ),
                    ]
                ),
            ],
            id=CANCEL_MODAL_WORKER_MANAGEMENT_ID,
            is_open=False,
        ),
    ]
)


# Callbacks


# Clientside callback: open loading overlay instantly in the browser.
# A server-side callback here would race with the processing callback
# (due to allow_duplicate), potentially leaving the overlay stuck open.
dash.clientside_callback(
    """
    function() {
        for (var i = 0; i < arguments.length; i++) {
            if (arguments[i] != null) return true;
        }
        return false;
    }
    """,
    Output(LOADING_OVERLAY_MODAL_SHARED_ID, "is_open", allow_duplicate=True),
    Input(REFRESH_BUTTON_WORKER_MANAGEMENT_ID, "n_clicks"),
    Input(KILL_BUTTON_WORKER_MANAGEMENT_ID, "n_clicks"),
    Input(CANCEL_BUTTON_WORKER_MANAGEMENT_ID, "n_clicks"),
    Input(DUMMY_DIV_WORKER_MANAGEMENT_ID, "data"),
    prevent_initial_call=True,
)


# Callback 2: Refresh all data
@callback(
    Output(STATS_CARD_DIV_WORKER_MANAGEMENT_ID, "children"),
    Output(ACTIVE_TASKS_TABLE_WORKER_MANAGEMENT_ID, "rowData"),
    Output(RESERVED_TASKS_TABLE_WORKER_MANAGEMENT_ID, "rowData"),
    Output(SCHEDULED_TASKS_TABLE_WORKER_MANAGEMENT_ID, "rowData"),
    Output(REVOKED_TASKS_TABLE_WORKER_MANAGEMENT_ID, "rowData"),
    Output(LAST_REFRESH_DIV_WORKER_MANAGEMENT_ID, "children"),
    Output(LOADING_OVERLAY_MODAL_SHARED_ID, "is_open", allow_duplicate=True),
    Input(REFRESH_BUTTON_WORKER_MANAGEMENT_ID, "n_clicks"),
    prevent_initial_call=True,
)
def refresh_data(refresh_clicks):
    """Refresh all worker and task data."""
    log.info("Refreshing worker data")

    overview = background_job_manager.get_all_tasks_overview()
    log.debug(f"Retrieved task overview: {overview}")

    # Format data for display
    worker_cards = format_worker_stats(overview)
    active_data = format_active_tasks(overview["active"])
    reserved_data = format_reserved_tasks(overview["reserved"])
    scheduled_data = format_scheduled_tasks(overview["scheduled"])
    revoked_data = format_revoked_tasks(overview["revoked"])

    timestamp = datetime.now().strftime("%H:%M:%S")
    last_refresh_text = f"Last refresh: {timestamp}"

    log.info(
        f"Refreshed: {len(active_data)} active, {len(reserved_data)} reserved, "
        f"{len(scheduled_data)} scheduled, {len(revoked_data)} revoked tasks",
    )

    return (
        worker_cards,
        active_data,
        reserved_data,
        scheduled_data,
        revoked_data,
        last_refresh_text,
        False,
    )


# Callback 4: Enable/disable kill button based on selection
@callback(
    Output(KILL_BUTTON_WORKER_MANAGEMENT_ID, "disabled"),
    Input(ACTIVE_TASKS_TABLE_WORKER_MANAGEMENT_ID, "selectedRows"),
)
def enable_kill_button(selected_rows):
    """Enable kill button only when a task is selected."""
    return not selected_rows


# Callback 5: Enable/disable cancel button based on selection
@callback(
    Output(CANCEL_BUTTON_WORKER_MANAGEMENT_ID, "disabled"),
    Input(RESERVED_TASKS_TABLE_WORKER_MANAGEMENT_ID, "selectedRows"),
    Input(SCHEDULED_TASKS_TABLE_WORKER_MANAGEMENT_ID, "selectedRows"),
)
def enable_cancel_button(reserved_selected, scheduled_selected):
    """Enable cancel button when a task is selected in either table."""
    return not (reserved_selected or scheduled_selected)


# Callback 6: Open kill confirmation modal
@callback(
    Output(KILL_MODAL_WORKER_MANAGEMENT_ID, "is_open"),
    Output(KILL_MODAL_TASK_INFO_DIV_WORKER_MANAGEMENT_ID, "children"),
    Input(KILL_BUTTON_WORKER_MANAGEMENT_ID, "n_clicks"),
    State(ACTIVE_TASKS_TABLE_WORKER_MANAGEMENT_ID, "selectedRows"),
    prevent_initial_call=True,
)
def open_kill_modal(n_clicks, selected_rows):
    """Open kill confirmation modal with task info."""
    if not selected_rows:
        return False, ""

    task = selected_rows[0]
    task_info = (
        f"Task: {task['task_name']}\n"
        f"ID: {task['task_id']}\n"
        f"Worker: {task['worker']}\n"
        f"Duration: {task['duration']}\n"
    )

    log.info(f"Opening kill modal for task {task['task_id']}")

    return True, task_info


# Callback 7: Confirm kill task
@callback(
    Output(KILL_MODAL_WORKER_MANAGEMENT_ID, "is_open", allow_duplicate=True),
    Output(ACTIVE_TASKS_TABLE_WORKER_MANAGEMENT_ID, "selectedRows"),
    Output(LOADING_OVERLAY_MODAL_SHARED_ID, "is_open", allow_duplicate=True),
    Input(KILL_MODAL_CONFIRM_BUTTON_WORKER_MANAGEMENT_ID, "n_clicks"),
    State(ACTIVE_TASKS_TABLE_WORKER_MANAGEMENT_ID, "selectedRows"),
    prevent_initial_call=True,
)
def confirm_kill_task(n_clicks, selected_rows):
    """Kill the selected task."""
    if not selected_rows:
        log.warning("Kill task attempted with no selection")
        # Close modal gracefully, no task to kill
        return False, [], False

    task = selected_rows[0]
    task_id = task["task_id"]

    background_job_manager.revoke_job(task_id, terminate=True)

    log.info(f"Killed task {task_id}")

    # Close modal, reset selection, hide overlay
    return False, [], False


# Callback 8: Cancel kill modal
@callback(
    Output(KILL_MODAL_WORKER_MANAGEMENT_ID, "is_open", allow_duplicate=True),
    Input(KILL_MODAL_CANCEL_BUTTON_WORKER_MANAGEMENT_ID, "n_clicks"),
    prevent_initial_call=True,
)
def cancel_kill_modal(n_clicks):
    """Close kill modal without action."""
    return False


# Callback 9: Open cancel confirmation modal
@callback(
    Output(CANCEL_MODAL_WORKER_MANAGEMENT_ID, "is_open"),
    Output(CANCEL_MODAL_TASK_INFO_DIV_WORKER_MANAGEMENT_ID, "children"),
    Input(CANCEL_BUTTON_WORKER_MANAGEMENT_ID, "n_clicks"),
    State(RESERVED_TASKS_TABLE_WORKER_MANAGEMENT_ID, "selectedRows"),
    State(SCHEDULED_TASKS_TABLE_WORKER_MANAGEMENT_ID, "selectedRows"),
    prevent_initial_call=True,
)
def open_cancel_modal(n_clicks, reserved_selected, scheduled_selected):
    """Open cancel confirmation modal with task info."""
    task = None
    if reserved_selected:
        task = reserved_selected[0]
    elif scheduled_selected:
        task = scheduled_selected[0]

    if not task:
        return False, ""

    task_info = (
        f"Task: {task['task_name']}\n"
        f"ID: {task['task_id']}\n"
        f"Queue: {task.get('queue', 'N/A')}\n"  # queue absent for active/revoked tasks
    )

    log.info(f"Opening cancel modal for task {task['task_id']}")

    return True, task_info


# Callback 10: Confirm cancel task
@callback(
    Output(CANCEL_MODAL_WORKER_MANAGEMENT_ID, "is_open", allow_duplicate=True),
    Output(RESERVED_TASKS_TABLE_WORKER_MANAGEMENT_ID, "selectedRows"),
    Output(SCHEDULED_TASKS_TABLE_WORKER_MANAGEMENT_ID, "selectedRows"),
    Output(LOADING_OVERLAY_MODAL_SHARED_ID, "is_open", allow_duplicate=True),
    Input(CANCEL_MODAL_CONFIRM_BUTTON_WORKER_MANAGEMENT_ID, "n_clicks"),
    State(RESERVED_TASKS_TABLE_WORKER_MANAGEMENT_ID, "selectedRows"),
    State(SCHEDULED_TASKS_TABLE_WORKER_MANAGEMENT_ID, "selectedRows"),
    prevent_initial_call=True,
)
def confirm_cancel_task(n_clicks, reserved_selected, scheduled_selected):
    """Cancel the selected task."""
    task = None
    if reserved_selected:
        task = reserved_selected[0]
    elif scheduled_selected:
        task = scheduled_selected[0]

    if not task:
        log.warning("Cancel task attempted with no selection")
        # Close modal gracefully, no task to cancel
        return False, [], [], False

    task_id = task["task_id"]

    background_job_manager.revoke_job(task_id, terminate=False)

    log.info(f"Cancelled task {task_id}")

    # Close modal, reset selections, hide overlay
    return False, [], [], False


# Callback 11: Cancel cancel modal
@callback(
    Output(CANCEL_MODAL_WORKER_MANAGEMENT_ID, "is_open", allow_duplicate=True),
    Input(CANCEL_MODAL_CANCEL_BUTTON_WORKER_MANAGEMENT_ID, "n_clicks"),
    prevent_initial_call=True,
)
def cancel_cancel_modal(n_clicks):
    """Close cancel modal without action."""
    return False
