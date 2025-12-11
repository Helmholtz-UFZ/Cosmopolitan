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
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dash_table, dcc, html

from cosmopolitan_app.constants import LOADING_OVERLAY_ID
from cosmopolitan_app.layouts import create_header, page_container_column_layout
from cosmopolitan_app.postgres_manager import PostgresManager
from cosmopolitan_app.timeio_manager import TimeIOManager

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
    return dash_table.DataTable(
        id="database-sensors-table",
        columns=[
            {
                "id": "sensor_id",
                "name": "Sensor ID",
                "type": "numeric",
                "editable": False,
            },
            {"id": "sensor_name", "name": "Name", "editable": False},
            {
                "id": "sensor_type",
                "name": "Type",
                "editable": False,
            },
            {"id": "ignored", "name": "Ignored", "type": "text", "editable": False},
            {
                "id": "stationary",
                "name": "Stationary",
                "type": "text",
                "editable": False,
            },
            {
                "id": "datastreams",
                "name": "Datastreams",
                "editable": False,
            },
        ],
        data=[],
        row_selectable="single",
        selected_rows=[],
        editable=True,
        dropdown={
            "sensor_type": {
                "options": [
                    {"label": "Station", "value": "station"},
                    {"label": "Train", "value": "train"},
                    {"label": "Rover", "value": "rover"},
                    {"label": "Unknown", "value": "unknown"},
                ]
            }
        },
        style_cell={"textAlign": "center", "fontSize": "12px"},
        style_data_conditional=[
            {
                "if": {"filter_query": "{ignored} = False", "column_id": "ignored"},
                "backgroundColor": "#d4edda",
                "color": "#155724",
            },
            {
                "if": {"filter_query": "{ignored} = True", "column_id": "ignored"},
                "backgroundColor": "#f8d7da",
                "color": "#721c24",
            },
            {
                "if": {
                    "filter_query": "{stationary} = True",
                    "column_id": "stationary",
                },
                "backgroundColor": "#e2e3e5",
            },
            {
                "if": {
                    "filter_query": "{stationary} = False",
                    "column_id": "stationary",
                },
                "backgroundColor": "#fff3cd",
            },
        ],
        sort_action="native",
        page_size=20,
        style_table={
            "height": "70vh",
            "overflowY": "auto",
            "paddingLeft": "4px",
        },
    )


def create_api_table():
    """Create the TimeIO API sensors table component."""
    return dash_table.DataTable(
        id="api-sensors-table",
        columns=[
            {"id": "sensor_id", "name": "ID", "type": "numeric"},
            {"id": "name", "name": "Name"},
            {"id": "status", "name": "Status"},
            {"id": "in_database", "name": "In DB"},
        ],
        data=[],
        row_selectable="single",
        selected_rows=[],
        style_cell={"textAlign": "center", "fontSize": "12px"},
        style_data_conditional=[
            {
                "if": {"filter_query": "{status} = 'active'", "column_id": "status"},
                "backgroundColor": "#d4edda",
                "color": "#155724",
            },
            {
                "if": {"filter_query": "{status} = 'ignored'", "column_id": "status"},
                "backgroundColor": "#f8d7da",
                "color": "#721c24",
            },
            {
                "if": {"filter_query": "{status} = 'new'", "column_id": "status"},
                "backgroundColor": "#fff3cd",
                "color": "#856404",
            },
            {
                "if": {
                    "filter_query": "{in_database} = True",
                    "column_id": "in_database",
                },
                "backgroundColor": "#d4edda",
                "color": "#155724",
            },
        ],
        sort_action="native",
        page_size=20,
        style_table={
            "height": "70vh",
            "overflowY": "auto",
            "paddingLeft": "4px",
        },
    )


edit_form = dbc.Form(
    [
        dbc.Row(
            [
                # Left column - Basic fields
                dbc.Col(
                    [
                        dbc.Label("Sensor ID", html_for="edit-sensor-id"),
                        dbc.Input(
                            id="edit-sensor-id",
                            type="text",
                            placeholder="Enter sensor ID",
                            className="mb-3",
                            disabled=True,
                        ),
                        dbc.Label(
                            "Sensor Type",
                            html_for="edit-sensor-type",
                        ),
                        dbc.Select(
                            id="edit-sensor-type",
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
                            html_for="edit-sensor-name",
                        ),
                        dbc.Input(
                            id="edit-sensor-name",
                            type="text",
                            placeholder="Enter sensor name",
                            className="mb-3",
                        ),
                        dbc.Label("Ignored Status"),
                        dbc.Switch(
                            id="edit-ignored",
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
                            html_for="edit-datastreams",
                        ),
                        dbc.Textarea(
                            id="edit-datastreams",
                            placeholder='{"datastream_id": "datastream_name", ...}',
                            rows=20,
                            className="mb-3",
                            style={
                                "fontFamily": "monospace",
                                "fontSize": "12px",
                            },
                        ),
                        dbc.FormFeedback(
                            id="datastreams-feedback",
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
                            "Update/Add Entry",
                            id="submit-edit-btn",
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
        dcc.Store(id="database-sensors-store", data=[]),
        dcc.Store(id="api-sensors-store", data=[]),
        dcc.Store(id="refresh-store", data=0),
        dcc.Store(id="dummy-store", data=0),  # For loading overlay
        # Sync Status Alert (centered above tables)
        dbc.Row(
            dbc.Col(
                dbc.Alert(
                    id="sync-status-alert",
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
                                    "Refresh Database",
                                    id="refresh-database-btn",
                                    color="primary",
                                    className="mb-3",
                                ),
                            ],
                            width=7,
                        ),
                        # Vertical separator
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
        Output("database-sensors-store", "data"),
        Output("database-sensors-table", "data"),
        Output("api-sensors-store", "data"),
        Output("api-sensors-table", "data"),
        Output("sync-status-alert", "children"),
        Output("sync-status-alert", "color"),
        Output("sync-status-alert", "is_open"),
        Output(LOADING_OVERLAY_ID, "is_open", allow_duplicate=True),
    ],
    [
        Input("refresh-database-btn", "n_clicks"),
        Input("refresh-store", "data"),
    ],
    prevent_initial_call=True,
)
def refresh_all_sensors(n_clicks, refresh_trigger):
    """Refresh both database and API sensors data."""
    logging.info("Refreshing all sensors data", extra={"tag": "time_io"})

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


@callback(
    Output(LOADING_OVERLAY_ID, "is_open", allow_duplicate=True),
    Input("refresh-database-btn", "n_clicks"),
    Input("refresh-store", "data"),
    Input("dummy-store", "data"),
    prevent_initial_call=True,
)
def show_loading(n_clicks, refresh_trigger, _dummy_data):
    """Show loading overlay when refresh button is clicked."""
    ctx = dash.callback_context
    if ctx.triggered:
        triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if triggered_id in ["refresh-database-btn", "refresh-store"]:
            return True


@callback(
    [
        Output("database-sensors-table", "selected_rows"),
        Output("api-sensors-table", "selected_rows"),
    ],
    [
        Input("database-sensors-table", "selected_rows"),
        Input("api-sensors-table", "selected_rows"),
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

    if triggered_id == "database-sensors-table":
        # Database table was selected, clear API selection
        return db_selected or [], []
    elif triggered_id == "api-sensors-table":
        # API table was selected, clear database selection
        return [], api_selected or []

    # Fallback - maintain current selections
    return db_selected or [], api_selected or []


@callback(
    [
        Output("edit-sensor-id", "value"),
        Output("edit-sensor-name", "value"),
        Output("edit-sensor-type", "value"),
        Output("edit-ignored", "value"),
        Output("edit-datastreams", "value"),
        Output("submit-edit-btn", "disabled"),
        Output("submit-edit-btn", "children"),
    ],
    [
        Input("database-sensors-table", "selected_rows"),
        Input("api-sensors-table", "selected_rows"),
    ],
    [
        State("database-sensors-table", "data"),
        State("database-sensors-store", "data"),
        State("api-sensors-table", "data"),
    ],
    prevent_initial_call=True,
)
def populate_edit_form(db_selected, api_selected, db_data, db_store_data, api_data):
    """Populate edit form based on table selection."""
    logging.info("Populating edit form based on selection", extra={"tag": "time_io"})
    if not db_selected and not api_selected:
        return (
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            True,
            "Update/Add Entry",
        )

    # Populate from database table selection
    if db_selected and db_data and db_store_data:
        row = db_data[db_selected[0]]
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
            "Update Entry",  # Database selection = update
        )

    # Populate from API table selection
    elif api_selected and api_data:
        row = api_data[api_selected[0]]
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
            "Add Entry",  # API selection = add new
        )


@callback(
    [
        Output("edit-datastreams", "invalid"),
        Output("datastreams-feedback", "children"),
        Output("submit-edit-btn", "disabled", allow_duplicate=True),
    ],
    [
        Input("edit-datastreams", "value"),
        Input("edit-sensor-type", "value"),
        Input("edit-ignored", "value"),
    ],
    [
        State("edit-sensor-id", "value"),
        State("edit-sensor-name", "value"),
    ],
    prevent_initial_call=True,
)
def validate_datastreams_json(json_value, sensor_type, ignored, sensor_id, sensor_name):
    """Validate datastreams JSON format and content with enhanced rules."""
    logging.info("Validating datastreams JSON", extra={"tag": "time_io"})
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
        Output("refresh-store", "data"),
    ],
    Input("submit-edit-btn", "n_clicks"),
    [
        State("edit-sensor-id", "value"),
        State("edit-sensor-name", "value"),
        State("edit-sensor-type", "value"),
        State("edit-ignored", "value"),
        State("edit-datastreams", "value"),
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

    logging.info(f"Submitting form for sensor ID {sensor_id}", extra={"tag": "time_io"})

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
