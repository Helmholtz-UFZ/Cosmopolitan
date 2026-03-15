"""Configure and manage cosmic ray neutron sensor settings.

This administrative page lets you manage the cosmic ray neutron sensors (CRNS) that
provide measurement data for predictions. Features include:

- View all configured sensors in a comparison table
- Compare database configuration with TimeIO API data
- Add new sensors or update existing sensor configurations
- Configure sensor datastreams (measurement channels)
- Validate sensor settings and datastream formats
- Mark sensors as ignored if they shouldn't be used for predictions

Sensors can be stationary stations, trains, or rovers, each with different datastream
requirements. The page validates that sensor configurations follow the correct format
and helps ensure data quality for prediction models.

NOTE: This docstring is displayed on the documentation webpage.
"""

import json
import logging

import dash
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html

from cosmopolitan_app.constants import (
    API_SENSORS_STORE_SENSOR_MANAGEMENT_ID,
    API_SENSORS_TABLE_SENSOR_MANAGEMENT_ID,
    DATABASE_SENSORS_STORE_SENSOR_MANAGEMENT_ID,
    DATABASE_SENSORS_TABLE_SENSOR_MANAGEMENT_ID,
    DATASTREAMS_FEEDBACK_SENSOR_MANAGEMENT_ID,
    EDIT_DATASTREAMS_TEXTAREA_SENSOR_MANAGEMENT_ID,
    EDIT_IGNORED_SWITCH_SENSOR_MANAGEMENT_ID,
    EDIT_SENSOR_INPUT_SENSOR_MANAGEMENT_ID,
    EDIT_SENSOR_NAME_INPUT_SENSOR_MANAGEMENT_ID,
    EDIT_SENSOR_TYPE_SELECT_SENSOR_MANAGEMENT_ID,
    LOADING_OVERLAY_MODAL_SHARED_ID,
    REFRESH_DATABASE_BUTTON_SENSOR_MANAGEMENT_ID,
    REFRESH_STORE_SENSOR_MANAGEMENT_ID,
    SUBMIT_EDIT_BUTTON_SENSOR_MANAGEMENT_ID,
    SYNC_STATUS_ALERT_SENSOR_MANAGEMENT_ID,
)
from cosmopolitan_app.layouts import create_header, page_container_column_layout
from cosmopolitan_app.postgres_manager import PostgresManager
from cosmopolitan_app.timeio_manager import TimeIOManager

log = logging.getLogger(__name__)

dash.register_page(__name__, path="/sensor_management")


def valid_datastreams(json_value, sensor_type, ignored=False) -> (bool, str):
    """Validate datastreams JSON format and content."""
    # Allowed measurement types
    allowed_measurements = ["Neutron counts", "soil_moisture"]
    try:
        parsed = json.loads(json_value)
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {str(e)}"

    if not isinstance(parsed, dict):
        return False, "Datastreams must be a JSON object/dictionary"

    for key in parsed.keys():
        if not isinstance(key, str):
            return False, "All datastream keys must be strings"

    # Check that dictionary is flat (not nested)
    for value in parsed.values():
        if isinstance(value, (dict, list)):
            return (
                False,
                "Datastreams dictionary must be flat (no nested objects or arrays)",
            )

    # If sensor is ignored, allow any dictionary structure
    if ignored:
        return True, ""

    datastream_values = list(parsed.values())
    datastream_count = len(datastream_values)

    if datastream_count != 1 and sensor_type == "station":
        return False, "Stationary sensors must have exactly 1 datastream"
    elif datastream_count != 3 and sensor_type in ["train", "rover"]:
        return False, "Mobile sensors must have exactly 3 datastreams"

    if datastream_count == 3:
        # For 3 datastreams: must have longitude, latitude, and one measurement
        if "longitude" not in datastream_values:
            return False, "3 datastreams must include 'longitude'"
        if "latitude" not in datastream_values:
            return False, "3 datastreams must include 'latitude'"

        # Check the third datastream
        other_values = [
            v for v in datastream_values if v not in ["longitude", "latitude"]
        ]
        if other_values[0] not in allowed_measurements:
            return (
                False,
                f"Third datastream must be one of: {', '.join(allowed_measurements)}",
            )

        # Suggest sensor type for mobile sensors
        if sensor_type not in ["train", "rover"]:
            return (
                False,
                "Sensors with longitude/latitude should be 'train' or 'rover' type",
            )

    elif datastream_count == 1:
        # For 1 datastream: must be a measurement type
        if datastream_values[0] not in allowed_measurements:
            return (
                False,
                f"Single datastream must be one of: {', '.join(allowed_measurements)}",
            )

        if sensor_type not in ["station"]:
            return (
                False,
                "Sensors with single measurement should be 'station' type",
            )

    return True, ""


def shorten_json_string(s):
    """Shorten a JSON string for display purposes."""
    max_length = 30
    if len(s) <= max_length:
        return s
    keep = (max_length - 3) // 2
    return s[:keep] + "..." + s[-keep:]


def create_database_table():
    """Create the database sensors table component."""
    return dag.AgGrid(
        id=DATABASE_SENSORS_TABLE_SENSOR_MANAGEMENT_ID,
        columnDefs=[
            {"field": "sensor_id", "headerName": "Sensor ID", "type": "numericColumn"},
            {"field": "sensor_name", "headerName": "Name"},
            {"field": "sensor_type", "headerName": "Type"},
            {
                "field": "ignored",
                "headerName": "Ignored",
                "cellStyle": {
                    "styleConditions": [
                        {
                            "condition": "params.value === 'False'",
                            "style": {"backgroundColor": "#d4edda", "color": "#155724"},
                        },
                        {
                            "condition": "params.value === 'True'",
                            "style": {"backgroundColor": "#f8d7da", "color": "#721c24"},
                        },
                    ],
                },
            },
            {
                "field": "stationary",
                "headerName": "Stationary",
                "cellStyle": {
                    "styleConditions": [
                        {
                            "condition": "params.value === 'True'",
                            "style": {"backgroundColor": "#e2e3e5"},
                        },
                        {
                            "condition": "params.value === 'False'",
                            "style": {"backgroundColor": "#fff3cd"},
                        },
                    ],
                },
            },
            {"field": "datastreams", "headerName": "Datastreams"},
        ],
        rowData=[],
        defaultColDef={
            "sortable": True,
            "resizable": True,
            "cellStyle": {"textAlign": "center", "fontSize": "12px"},
        },
        dashGridOptions={
            "rowSelection": {"mode": "singleRow"},
            "pagination": True,
            "paginationPageSize": 20,
        },
        # AG Grid height set via style since Bootstrap has no 70vh utility
        style={"height": "70vh"},
        columnSize="responsiveSizeToFit",
    )


def create_api_table():
    """Create the TimeIO API sensors table component."""
    return dag.AgGrid(
        id=API_SENSORS_TABLE_SENSOR_MANAGEMENT_ID,
        columnDefs=[
            {"field": "sensor_id", "headerName": "ID", "type": "numericColumn"},
            {"field": "name", "headerName": "Name"},
            {
                "field": "status",
                "headerName": "Status",
                "cellStyle": {
                    "styleConditions": [
                        {
                            "condition": "params.value === 'active'",
                            "style": {"backgroundColor": "#d4edda", "color": "#155724"},
                        },
                        {
                            "condition": "params.value === 'ignored'",
                            "style": {"backgroundColor": "#f8d7da", "color": "#721c24"},
                        },
                        {
                            "condition": "params.value === 'new'",
                            "style": {"backgroundColor": "#fff3cd", "color": "#856404"},
                        },
                    ],
                },
            },
            {
                "field": "in_database",
                "headerName": "In DB",
                "cellStyle": {
                    "styleConditions": [
                        {
                            "condition": "params.value === 'True'",
                            "style": {"backgroundColor": "#d4edda", "color": "#155724"},
                        },
                    ],
                },
            },
        ],
        rowData=[],
        defaultColDef={
            "sortable": True,
            "resizable": True,
            "cellStyle": {"textAlign": "center", "fontSize": "12px"},
        },
        dashGridOptions={
            "rowSelection": {"mode": "singleRow"},
            "pagination": True,
            "paginationPageSize": 20,
        },
        style={"height": "70vh"},
        columnSize="responsiveSizeToFit",
    )


edit_form = dbc.Form(
    [
        dbc.Row(
            [
                # Left column - Basic fields
                dbc.Col(
                    [
                        dbc.Label(
                            "Sensor ID", html_for=EDIT_SENSOR_INPUT_SENSOR_MANAGEMENT_ID
                        ),
                        dbc.Input(
                            id=EDIT_SENSOR_INPUT_SENSOR_MANAGEMENT_ID,
                            type="text",
                            placeholder="Enter sensor ID",
                            className="mb-3",
                            disabled=True,
                        ),
                        dbc.Label(
                            "Sensor Type",
                            html_for=EDIT_SENSOR_TYPE_SELECT_SENSOR_MANAGEMENT_ID,
                        ),
                        dbc.Select(
                            id=EDIT_SENSOR_TYPE_SELECT_SENSOR_MANAGEMENT_ID,
                            options=[
                                {
                                    "label": "Station",
                                    "value": "station",
                                },
                                {
                                    "label": "Train",
                                    "value": "train",
                                },
                                {
                                    "label": "Rover",
                                    "value": "rover",
                                },
                                {
                                    "label": "Unknown",
                                    "value": "unknown",
                                },
                            ],
                            className="mb-3",
                        ),
                        dbc.Label(
                            "Sensor Name",
                            html_for=EDIT_SENSOR_NAME_INPUT_SENSOR_MANAGEMENT_ID,
                        ),
                        dbc.Input(
                            id=EDIT_SENSOR_NAME_INPUT_SENSOR_MANAGEMENT_ID,
                            type="text",
                            placeholder="Enter sensor name",
                            className="mb-3",
                        ),
                        dbc.Label("Ignored Status"),
                        dbc.Switch(
                            id=EDIT_IGNORED_SWITCH_SENSOR_MANAGEMENT_ID,
                            label="Is Ignored",
                            value=False,
                            className="mb-3",
                        ),
                    ],
                    width=6,
                ),
                # Right column - JSON field
                dbc.Col(
                    [
                        dbc.Label(
                            "Datastreams (JSON)",
                            html_for=EDIT_DATASTREAMS_TEXTAREA_SENSOR_MANAGEMENT_ID,
                        ),
                        dbc.Textarea(
                            id=EDIT_DATASTREAMS_TEXTAREA_SENSOR_MANAGEMENT_ID,
                            placeholder='{"datastream_id": "datastream_name", ...}',
                            rows=20,
                            className="mb-3",
                            # font-monospace only works on text elements, not textarea;
                            # Bootstrap has no utility for 12px font size
                            style={
                                "fontFamily": "monospace",
                                "fontSize": "12px",
                            },
                        ),
                        dbc.FormFeedback(
                            id=DATASTREAMS_FEEDBACK_SENSOR_MANAGEMENT_ID,
                            type="invalid",
                        ),
                    ],
                    width=6,
                ),
            ]
        ),
        # Bottom row - Centered button
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Button(
                            [
                                html.I(className="bi bi-check-circle me-1"),
                                "Update/Add Entry",
                            ],
                            id=SUBMIT_EDIT_BUTTON_SENSOR_MANAGEMENT_ID,
                            color="success",
                            className="mt-3",
                            disabled=True,
                        ),
                    ],
                    width=12,
                    className="d-flex justify-content-center",
                ),
            ]
        ),
    ]
)

layout = page_container_column_layout(
    [
        create_header(
            "Sensor Management",
            "Manage sensor configurations and synchronize with TimeIO API",
        ),
        # Store components for data
        dcc.Store(id=DATABASE_SENSORS_STORE_SENSOR_MANAGEMENT_ID, data=[]),
        dcc.Store(id=API_SENSORS_STORE_SENSOR_MANAGEMENT_ID, data=[]),
        dcc.Store(id=REFRESH_STORE_SENSOR_MANAGEMENT_ID, data=0),
        # Sync Status Alert (centered above tables)
        dbc.Row(
            dbc.Col(
                dbc.Alert(
                    id=SYNC_STATUS_ALERT_SENSOR_MANAGEMENT_ID,
                    className="text-center m-3",
                    is_open=False,
                ),
                className="col-auto",
            ),
            className="d-flex justify-content-center",
        ),
        # Main content - two columns with border separator
        html.Div(
            [
                dbc.Row(
                    [
                        # Left column - Database view
                        dbc.Col(
                            [
                                html.H4("Database Sensors", className="mb-3"),
                                html.P(
                                    "Sensors currently stored in the database:",
                                    className="text-muted",
                                ),
                                create_database_table(),
                                dbc.Button(
                                    [
                                        html.I(className="bi bi-arrow-clockwise me-1"),
                                        "Refresh Database",
                                    ],
                                    id=REFRESH_DATABASE_BUTTON_SENSOR_MANAGEMENT_ID,
                                    color="primary",
                                    className="mb-3",
                                ),
                            ],
                            width=7,
                        ),
                        # Vertical separator — no Bootstrap class for 1px-wide divider
                        html.Div(
                            style={
                                "width": "1px",
                            }
                        ),
                        # Right column - API view
                        dbc.Col(
                            [
                                html.H4("API Sensors", className="mb-3"),
                                html.P(
                                    "Sensors available from TimeIO API:",
                                    className="text-muted",
                                ),
                                create_api_table(),
                            ],
                            width=4,
                        ),
                    ],
                    className="g-3 justify-content-center",
                )
            ],
            className="py-3",
        ),
        # Edit Form Section in Card
        dbc.Card(
            [
                dbc.CardHeader([html.H4("Edit Sensor Entry", className="mb-0")]),
                dbc.CardBody(edit_form),
            ],
            className="m-4",
        ),
    ]
)


@callback(
    [
        Output(DATABASE_SENSORS_STORE_SENSOR_MANAGEMENT_ID, "data"),
        Output(DATABASE_SENSORS_TABLE_SENSOR_MANAGEMENT_ID, "rowData"),
        Output(API_SENSORS_STORE_SENSOR_MANAGEMENT_ID, "data"),
        Output(API_SENSORS_TABLE_SENSOR_MANAGEMENT_ID, "rowData"),
        Output(SYNC_STATUS_ALERT_SENSOR_MANAGEMENT_ID, "children"),
        Output(SYNC_STATUS_ALERT_SENSOR_MANAGEMENT_ID, "color"),
        Output(SYNC_STATUS_ALERT_SENSOR_MANAGEMENT_ID, "is_open"),
        Output(LOADING_OVERLAY_MODAL_SHARED_ID, "is_open", allow_duplicate=True),
    ],
    [
        Input(REFRESH_DATABASE_BUTTON_SENSOR_MANAGEMENT_ID, "n_clicks"),
        Input(REFRESH_STORE_SENSOR_MANAGEMENT_ID, "data"),
    ],
    prevent_initial_call=True,
)
def refresh_all_sensors(n_clicks, refresh_trigger):
    """Refresh both database and API sensors data."""
    log.info("Refreshing all sensors data")

    # First, refresh database sensors
    sensors = PostgresManager.get_all_timeio_sensors(not_ignored_only=False)

    # Format database data for display
    db_table_data = []
    for sensor in sensors:
        db_table_data.append(
            {
                "sensor_id": sensor["sensor_id"],
                "sensor_name": sensor["sensor_name"],
                "sensor_type": sensor["sensor_type"],
                "ignored": str(sensor["ignored"]),
                "stationary": str(sensor["stationary"]),
                "datastreams": shorten_json_string(json.dumps(sensor["datastreams"])),
            }
        )

    # Then, refresh API sensors using database data
    api_things = TimeIOManager.get_things()
    database_ids = {s["sensor_id"] for s in sensors}
    ignore_things = TimeIOManager.get_ignore_things()

    # Format API data for display
    api_table_data = []
    for thing in api_things:
        sensor_id = thing["@iot.id"]

        # Determine status
        if sensor_id in ignore_things:
            status = "ignored"
        elif sensor_id in database_ids:
            status = "active"
        else:
            status = "new"

        api_table_data.append(
            {
                "sensor_id": sensor_id,
                "name": thing["name"],
                "status": status,
                "in_database": str(sensor_id in database_ids),
            }
        )

    # Check sync status between database and API
    api_sensor_ids = {thing["@iot.id"] for thing in api_things}
    db_sensor_ids = {sensor["sensor_id"] for sensor in sensors}

    # Find differences
    missing_from_db = api_sensor_ids - db_sensor_ids
    missing_from_api = db_sensor_ids - api_sensor_ids

    # Generate sync status
    if not missing_from_db and not missing_from_api:
        sync_message = "Database and TimeIO API are in sync"
        sync_color = "success"
        show_alert = True
    else:
        sync_parts = []
        if missing_from_db:
            sync_parts.append(f"{len(missing_from_db)} sensors missing from database")
        if missing_from_api:
            sync_parts.append(f"{len(missing_from_api)} sensors missing from API")
        sync_message = f"Out of sync: {', '.join(sync_parts)}"
        sync_color = "warning"
        show_alert = True

    return (
        sensors,
        db_table_data,
        api_things,
        api_table_data,
        sync_message,
        sync_color,
        show_alert,
        False,
    )


# Clientside callback: open loading overlay instantly in the browser.
# A server-side callback here would race with the processing callback
# (due to allow_duplicate), potentially leaving the overlay stuck open.
# Only listens to refresh triggers — not DUMMY_STORE (which should not show overlay).
dash.clientside_callback(
    "function(n) { return !!n; }",
    Output(LOADING_OVERLAY_MODAL_SHARED_ID, "is_open", allow_duplicate=True),
    Input(REFRESH_DATABASE_BUTTON_SENSOR_MANAGEMENT_ID, "n_clicks"),
    prevent_initial_call=True,
)


@callback(
    [
        Output(DATABASE_SENSORS_TABLE_SENSOR_MANAGEMENT_ID, "selectedRows"),
        Output(API_SENSORS_TABLE_SENSOR_MANAGEMENT_ID, "selectedRows"),
    ],
    [
        Input(DATABASE_SENSORS_TABLE_SENSOR_MANAGEMENT_ID, "selectedRows"),
        Input(API_SENSORS_TABLE_SENSOR_MANAGEMENT_ID, "selectedRows"),
    ],
    prevent_initial_call=True,
)
def handle_cross_table_selection(db_selected, api_selected):
    """Handle mutual exclusion between table selections."""
    ctx = dash.callback_context
    if not ctx.triggered:
        return db_selected or [], api_selected or []

    # Determine which input triggered the callback
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if triggered_id == DATABASE_SENSORS_TABLE_SENSOR_MANAGEMENT_ID:
        # Database table was selected, clear API selection
        return db_selected or [], []
    elif triggered_id == API_SENSORS_TABLE_SENSOR_MANAGEMENT_ID:
        # API table was selected, clear database selection
        return [], api_selected or []

    # Fallback - maintain current selections
    return db_selected or [], api_selected or []


@callback(
    [
        Output(EDIT_SENSOR_INPUT_SENSOR_MANAGEMENT_ID, "value"),
        Output(EDIT_SENSOR_NAME_INPUT_SENSOR_MANAGEMENT_ID, "value"),
        Output(EDIT_SENSOR_TYPE_SELECT_SENSOR_MANAGEMENT_ID, "value"),
        Output(EDIT_IGNORED_SWITCH_SENSOR_MANAGEMENT_ID, "value"),
        Output(EDIT_DATASTREAMS_TEXTAREA_SENSOR_MANAGEMENT_ID, "value"),
        Output(SUBMIT_EDIT_BUTTON_SENSOR_MANAGEMENT_ID, "disabled"),
        Output(SUBMIT_EDIT_BUTTON_SENSOR_MANAGEMENT_ID, "children"),
    ],
    [
        Input(DATABASE_SENSORS_TABLE_SENSOR_MANAGEMENT_ID, "selectedRows"),
        Input(API_SENSORS_TABLE_SENSOR_MANAGEMENT_ID, "selectedRows"),
    ],
    [
        State(DATABASE_SENSORS_STORE_SENSOR_MANAGEMENT_ID, "data"),
    ],
    prevent_initial_call=True,
)
def populate_edit_form(db_selected, api_selected, db_store_data):
    """Populate edit form based on table selection."""
    log.info("Populating edit form based on selection")
    if not db_selected and not api_selected:
        return (
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            True,
            [html.I(className="bi bi-check-circle me-1"), "Update/Add Entry"],
        )

    # Populate from database table selection
    if db_selected and db_store_data:
        row = db_selected[0]
        sensor_id = row["sensor_id"]

        # Find the corresponding sensor in store data for full JSON
        store_sensor = None
        for sensor in db_store_data:
            if sensor["sensor_id"] == sensor_id:
                store_sensor = sensor
                break

        # Format JSON for better readability from store data
        if store_sensor and store_sensor["datastreams"]:
            formatted_json = json.dumps(store_sensor["datastreams"], indent=2)
        else:
            formatted_json = "{}"

        return (
            row["sensor_id"],
            row["sensor_name"],
            row["sensor_type"],
            row["ignored"] == "True",
            formatted_json,
            False,  # Enable submit button
            [
                html.I(className="bi bi-check-circle me-1"),
                "Update Entry",
            ],  # Database selection = update
        )

    # Populate from API table selection
    elif api_selected:
        row = api_selected[0]
        sensor_id = row["sensor_id"]

        # Get datastreams from TimeIO API
        datastreams = TimeIOManager.get_datastreams_of_thing(sensor_id)
        datastreams = (
            {str(ds["@iot.id"]): ds["name"] for ds in datastreams}
            if datastreams
            else {}
        )
        formatted_json = json.dumps(datastreams, indent=2) if datastreams else "{}"

        # Convert API data to database format
        return (
            sensor_id,
            row["name"],
            "station",  # Default type, user can change
            False,  # Default not ignored
            formatted_json,
            False,  # Enable submit button
            [
                html.I(className="bi bi-plus-circle me-1"),
                "Add Entry",
            ],  # API selection = add new
        )


@callback(
    [
        Output(EDIT_DATASTREAMS_TEXTAREA_SENSOR_MANAGEMENT_ID, "invalid"),
        Output(DATASTREAMS_FEEDBACK_SENSOR_MANAGEMENT_ID, "children"),
        Output(
            SUBMIT_EDIT_BUTTON_SENSOR_MANAGEMENT_ID, "disabled", allow_duplicate=True
        ),
    ],
    [
        Input(EDIT_DATASTREAMS_TEXTAREA_SENSOR_MANAGEMENT_ID, "value"),
        Input(EDIT_SENSOR_TYPE_SELECT_SENSOR_MANAGEMENT_ID, "value"),
        Input(EDIT_IGNORED_SWITCH_SENSOR_MANAGEMENT_ID, "value"),
    ],
    [
        State(EDIT_SENSOR_INPUT_SENSOR_MANAGEMENT_ID, "value"),
        State(EDIT_SENSOR_NAME_INPUT_SENSOR_MANAGEMENT_ID, "value"),
    ],
    prevent_initial_call=True,
)
def validate_datastreams_json(json_value, sensor_type, ignored, sensor_id, sensor_name):
    """Validate datastreams JSON format and content with enhanced rules."""
    log.info("Validating datastreams JSON")
    if sensor_id is None:
        return dash.no_update, dash.no_update, True

    if not json_value or not json_value.strip():
        return True, "JSON is required", True

    json_valid, message = valid_datastreams(json_value, sensor_type, ignored)

    # Check if all required form fields are filled and json is valid
    if not sensor_id or not sensor_name or not sensor_type or not json_valid:
        submit_disabled = True
    else:
        submit_disabled = False

    return not json_valid, message, submit_disabled


@callback(
    [
        Output(REFRESH_STORE_SENSOR_MANAGEMENT_ID, "data"),
    ],
    Input(SUBMIT_EDIT_BUTTON_SENSOR_MANAGEMENT_ID, "n_clicks"),
    [
        State(EDIT_SENSOR_INPUT_SENSOR_MANAGEMENT_ID, "value"),
        State(EDIT_SENSOR_NAME_INPUT_SENSOR_MANAGEMENT_ID, "value"),
        State(EDIT_SENSOR_TYPE_SELECT_SENSOR_MANAGEMENT_ID, "value"),
        State(EDIT_IGNORED_SWITCH_SENSOR_MANAGEMENT_ID, "value"),
        State(EDIT_DATASTREAMS_TEXTAREA_SENSOR_MANAGEMENT_ID, "value"),
    ],
    prevent_initial_call=True,
)
def handle_form_submit(
    n_clicks,
    sensor_id,
    sensor_name,
    sensor_type,
    ignored,
    datastreams_json,
):
    """Handle form submission to update/add sensor entry."""
    if not n_clicks:
        return dash.no_update

    # Should not happen due to button disabling, but double-check
    if not sensor_id or not sensor_name or not sensor_type:
        return dash.no_update

    log.info(f"Submitting form for sensor ID {sensor_id}")

    json_valid, message = valid_datastreams(datastreams_json, sensor_type, ignored)
    # Should not happen due to validation, but double-check
    if not json_valid:
        return dash.no_update

    datastreams = json.loads(datastreams_json)

    # Prepare sensor data
    sensor_data = {
        "sensor_id": int(sensor_id),
        "sensor_name": sensor_name,
        "sensor_type": sensor_type,
        "ignored": ignored,
        "datastreams": datastreams,
    }

    PostgresManager.add_timeio_sensor(sensor_data)
    return [0]
