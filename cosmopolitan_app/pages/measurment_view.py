"""Measurement Database Dashboard for Cosmopolitan App."""

import logging
from datetime import date, datetime, timedelta

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, State, callback, dash_table, dcc, html
from pyproj import Transformer

from cosmopolitan_app.job import draw_preview
from cosmopolitan_app.layouts import create_header
from cosmopolitan_app.postgres_manager import PostgresManager
from cosmopolitan_app.timeio_info import type_id_dict

dash.register_page(__name__)

# Get available measurement types from type_id_dict
available_types = list(set(type_id_dict.values()))

# Create the measurement data table
measurement_table = dash_table.DataTable(
    id="measurements-table",
    columns=[
        {"id": "date_time", "name": "Date Time"},
        {"id": "sensor_id", "name": "Sensor ID"},
        {"id": "sensor_name", "name": "Sensor Name"},
        {
            "id": "soil_moisture",
            "name": "Soil Moisture",
            "type": "numeric",
            "format": {"specifier": ".3f"},
        },
        {
            "id": "error_high",
            "name": "Error High",
            "type": "numeric",
            "format": {"specifier": ".3f"},
        },
        {
            "id": "error_low",
            "name": "Error Low",
            "type": "numeric",
            "format": {"specifier": ".3f"},
        },
        {
            "id": "latitude",
            "name": "Latitude",
            "type": "numeric",
            "format": {"specifier": ".6f"},
        },
        {
            "id": "longitude",
            "name": "Longitude",
            "type": "numeric",
            "format": {"specifier": ".6f"},
        },
        {"id": "representative", "name": "Representative"},
    ],
    data=[],
    sort_action="native",
    filter_action="native",
    page_action="native",
    page_current=0,
    page_size=20,
    style_cell={
        "textAlign": "center",
        "fontSize": "12px",
        "padding": "8px",
    },
    style_header={
        "backgroundColor": "#f8f9fa",
        "fontWeight": "bold",
        "border": "1px solid #dee2e6",
    },
    style_data={
        "border": "1px solid #dee2e6",
    },
    style_data_conditional=[
        {
            "if": {"column_id": "sensor_name"},
            "textAlign": "left",
        },
        {
            "if": {"filter_query": "{representative} = true"},
            "backgroundColor": "#e8f5e8",
        },
    ],
    tooltip_data=[],
    tooltip_duration=None,
)

# Filter controls
filter_controls = dbc.Card(
    [
        dbc.CardBody(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Label(
                                    "Measurement Types:", className="form-label"
                                ),
                                dcc.Dropdown(
                                    id="type-dropdown",
                                    options=[
                                        {"label": t, "value": t}
                                        for t in available_types
                                    ],
                                    value=(
                                        available_types[:3]
                                        if len(available_types) >= 3
                                        else available_types
                                    ),
                                    multi=True,
                                    placeholder="Select measurement types...",
                                ),
                            ],
                            md=4,
                        ),
                        dbc.Col(
                            [
                                html.Label("Date Range:", className="form-label"),
                                dcc.DatePickerRange(
                                    id="date-range-picker",
                                    start_date=date(2024, 2, 1),
                                    end_date=date(2024, 2, 29),
                                    display_format="YYYY-MM-DD",
                                    style={"width": "100%"},
                                ),
                            ],
                            md=4,
                        ),
                        dbc.Col(
                            [
                                html.Label(
                                    "Representative Only:", className="form-label"
                                ),
                                dbc.Switch(
                                    id="representative-switch",
                                    label="Show only representative measurements",
                                    value=False,
                                ),
                            ],
                            md=4,
                        ),
                    ],
                    className="mb-3",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Label(
                                    "Bounding Box & Projection:",
                                    className="form-label",
                                ),
                                dbc.InputGroup(
                                    [
                                        dbc.InputGroupText("X1"),
                                        dbc.Input(
                                            id="bbox-min-lon",
                                            type="number",
                                            value=580000,
                                            step=1,
                                        ),
                                        dbc.InputGroupText("Y1"),
                                        dbc.Input(
                                            id="bbox-min-lat",
                                            type="number",
                                            value=5710000,
                                            step=1,
                                        ),
                                        dbc.InputGroupText("X2"),
                                        dbc.Input(
                                            id="bbox-max-lon",
                                            type="number",
                                            value=660000,
                                            step=1,
                                        ),
                                        dbc.InputGroupText("Y2"),
                                        dbc.Input(
                                            id="bbox-max-lat",
                                            type="number",
                                            value=5777000,
                                            step=1,
                                        ),
                                        dbc.InputGroupText("EPSG:"),
                                        dbc.Input(
                                            id="projection-input",
                                            type="text",
                                            value="25832",
                                        ),
                                    ],
                                    id="bbox-input-group",
                                    size="sm",
                                ),
                                dbc.FormText(
                                    id="transformation-feedback",
                                    className="text-danger",
                                    style={"display": "none"},
                                ),
                            ],
                            md=8,
                        ),
                        dbc.Col(
                            [
                                html.Label("Actions:", className="form-label"),
                                dbc.ButtonGroup(
                                    [
                                        dbc.Button(
                                            "Load Data",
                                            id="load-btn",
                                            color="primary",
                                            size="sm",
                                        ),
                                        dbc.Button(
                                            "Export CSV",
                                            id="export-btn",
                                            color="success",
                                            size="sm",
                                            disabled=True,
                                        ),
                                    ],
                                    className="d-flex",
                                ),
                            ],
                            md=4,
                        ),
                    ]
                ),
            ]
        ),
    ],
    className="mb-3",
)

# Statistics card
stats_card = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H5("Data Statistics", className="card-title text-center"),
                html.Div(id="stats-content"),
            ]
        ),
    ],
    className="mb-3",
)

preview_card = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H5("Area Preview", className="card-title text-center mb-3"),
                dbc.Spinner(
                    html.Div(id="preview-image", style={"text-align": "center"}),
                    color="primary",
                ),
            ]
        ),
    ],
    className="mb-3",
)

layout = [
    create_header(
        "Measurements",
        "View and analyze measurement data",
        bg_color="bg-info",
    ),
    dbc.Row(
        [
            dbc.Col(
                [
                    filter_controls,
                ],
                className="m-3",
            ),
        ]
    ),
    dbc.Row(
        [
            dbc.Col(
                [
                    preview_card,
                ],
                className="m-3",
            ),
        ]
    ),
    dbc.Row(
        [
            dbc.Col(
                [
                    stats_card,
                ],
                className="mx-3",
            ),
        ]
    ),
    dbc.Row(
        [
            dbc.Col(
                [
                    dbc.Spinner(
                        [
                            measurement_table,
                        ],
                        color="primary",
                    ),
                ],
                className="m-3",
            ),
        ]
    ),
    # Hidden div to store the current data for export
    html.Div(id="current-data-store", style={"display": "none"}),
    # Download component for CSV export
    dcc.Download(id="download-csv"),
]


def create_coordinate_transformer(source_proj, target_proj="EPSG:4326"):
    """Create a coordinate transformer from source to target projection."""
    # Ensure source projection has EPSG: prefix if it's just a number
    if source_proj.isdigit():
        source_proj = f"EPSG:{source_proj}"
    elif not source_proj.startswith("EPSG:"):
        source_proj = f"EPSG:{source_proj}"

    # Ensure target projection has EPSG: prefix if it's just a number
    if target_proj.isdigit():
        target_proj = f"EPSG:{target_proj}"
    elif not target_proj.startswith("EPSG:"):
        target_proj = f"EPSG:{target_proj}"

    transformer = Transformer.from_crs(source_proj, target_proj, always_xy=True)
    return transformer


def transform_bbox_coordinates(bbox, source_proj, target_proj="EPSG:4326"):
    """Transform bounding box coordinates from source to target projection."""
    transformer = create_coordinate_transformer(source_proj, target_proj)

    # Transform coordinates
    min_x, min_y = transformer.transform(bbox[0], bbox[1])
    max_x, max_y = transformer.transform(bbox[2], bbox[3])
    return [min_x, min_y, max_x, max_y]


def transform_coordinates_to_projection(df, target_proj="EPSG:4326"):
    """Transform longitude/latitude coordinates to specified projection for display."""
    if df.empty or target_proj == "4326":
        return df

    transformer = create_coordinate_transformer("EPSG:4326", target_proj)

    # Transform coordinates
    df_copy = df.copy()
    if "longitude" in df_copy.columns and "latitude" in df_copy.columns:
        # Filter out rows with NaN coordinates
        valid_coords = df_copy[["longitude", "latitude"]].notna().all(axis=1)
        if valid_coords.any():
            transformed_coords = transformer.transform(
                df_copy.loc[valid_coords, "longitude"].values,
                df_copy.loc[valid_coords, "latitude"].values,
            )
            df_copy.loc[valid_coords, "longitude"] = transformed_coords[0]
            df_copy.loc[valid_coords, "latitude"] = transformed_coords[1]

    return df_copy


@callback(
    Output("preview-image", "children"),
    [Input("load-btn", "n_clicks")],
    [
        State("type-dropdown", "value"),
        State("date-range-picker", "start_date"),
        State("date-range-picker", "end_date"),
        State("bbox-min-lon", "value"),
        State("bbox-min-lat", "value"),
        State("bbox-max-lon", "value"),
        State("bbox-max-lat", "value"),
        State("projection-input", "value"),
    ],
    prevent_initial_call=True,
)
def update_preview_image(
    n_clicks,
    selected_types,
    start_date,
    end_date,
    min_lon,
    min_lat,
    max_lon,
    max_lat,
    projection,
):
    """Update the preview image independently of the data loading."""
    if not n_clicks or not selected_types:
        return html.P(
            "No preview available. Please select filters and click 'Load Data'.",
            className="text-muted",
        )

    # Convert date strings to datetime objects
    start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
    end_datetime = (
        datetime.strptime(end_date, "%Y-%m-%d")
        + timedelta(days=1)
        - timedelta(seconds=1)
    )

    # Create bounding box
    bbox = [min_lon, min_lat, max_lon, max_lat]

    # Transform coordinates if projection is not WGS84 (EPSG:4326)
    if projection and projection != "4326":
        bbox = transform_bbox_coordinates(bbox, projection, "EPSG:4326")

    # Generate preview image (always generate, even if no data points)
    img_data = draw_preview(
        None,  # filepath=None returns base64
        bbox[0],  # min_lon
        bbox[1],  # min_lat
        bbox[2],  # max_lon
        bbox[3],  # max_lat
        selected_types,
        start_datetime,
        end_datetime,
    )

    # Create HTML image element
    preview_element = html.Div(
        [
            html.Img(
                src=f"data:image/png;base64,{img_data}",
                style={
                    "max-width": "100%",
                    "height": "auto",
                    "border": "1px solid #dee2e6",
                    "border-radius": "4px",
                    "box-shadow": "0 2px 4px rgba(0,0,0,0.1)",
                },
            ),
            html.P(
                "Green area shows the selected bounding box. Markers show measurement points (Green: train, Blue: station, Red: rover).",  # noqa
                className="text-muted text-center mt-2",
                style={"font-size": "12px"},
            ),
        ]
    )

    return preview_element


@callback(
    [
        Output("measurements-table", "data"),
        Output("stats-content", "children"),
        Output("export-btn", "disabled"),
        Output("current-data-store", "children"),
        Output("bbox-input-group", "invalid"),
        Output("transformation-feedback", "children"),
        Output("transformation-feedback", "style"),
    ],
    [Input("load-btn", "n_clicks")],
    [
        State("type-dropdown", "value"),
        State("date-range-picker", "start_date"),
        State("date-range-picker", "end_date"),
        State("representative-switch", "value"),
        State("bbox-min-lon", "value"),
        State("bbox-min-lat", "value"),
        State("bbox-max-lon", "value"),
        State("bbox-max-lat", "value"),
        State("projection-input", "value"),
    ],
    prevent_initial_call=True,
)
def load_measurement_data(
    n_clicks,
    selected_types,
    start_date,
    end_date,
    representative_only,
    min_lon,
    min_lat,
    max_lon,
    max_lat,
    projection,
):
    """Load measurement data based on the selected filters."""
    if not n_clicks or not selected_types:
        return (
            [],
            html.P("No data loaded. Please select filters and click 'Load Data'."),
            True,
            "",
            False,
            "",
            {"display": "none"},
        )

    logging.info(
        f"Loading measurement data with filters: types={selected_types}, "
        f"date_range={start_date} to {end_date}, representative={representative_only}, "
        f"bbox=({min_lon}, {min_lat}, {max_lon}, {max_lat}), projection={projection}"
    )

    # Convert date strings to datetime objects
    start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
    end_datetime = (
        datetime.strptime(end_date, "%Y-%m-%d")
        + timedelta(days=1)
        - timedelta(seconds=1)
    )

    # Create bounding box
    bbox = [min_lon, min_lat, max_lon, max_lat]

    # Transform coordinates if projection is not WGS84 (EPSG:4326)
    if projection and projection != "4326":
        bbox = transform_bbox_coordinates(bbox, projection, "EPSG:4326")
        logging.info(f"Transformed bbox from EPSG:{projection} to EPSG:4326: {bbox}")

    # Get measurement data
    df = PostgresManager.get_measurement_points(
        bbox=bbox,
        types=selected_types,
        start_date=start_datetime,
        end_date=end_datetime,
        representative=representative_only,
    )

    if df.empty:
        stats_content = html.P(
            "No data found for the selected filters.", className="text-muted"
        )
        return (
            [],
            stats_content,
            True,
            "",
            False,
            "",
            {"display": "none"},
        )

    # Transform coordinates back to display projection for the table
    if projection and projection != "4326":
        df_display = transform_coordinates_to_projection(df, projection)
    else:
        df_display = df.copy()

    # Convert DataFrame to table data
    table_data = df_display.to_dict("records")

    # Format datetime columns
    for record in table_data:
        if "date_time" in record and record["date_time"]:
            if isinstance(record["date_time"], datetime):
                record["date_time"] = record["date_time"].strftime("%Y-%m-%d %H:%M:%S")
        # Format boolean representative column
        if "representative" in record:
            record["representative"] = "Yes" if record["representative"] else "No"

    # Generate statistics
    stats_content = generate_stats(df)

    # Store original data (in WGS84) for export (convert to JSON string)
    export_data = df.to_json(orient="records", date_format="iso")

    return (
        table_data,
        stats_content,
        False,
        export_data,
        False,
        "",
        {"display": "none"},
    )


@callback(
    Output("download-csv", "data"),
    [Input("export-btn", "n_clicks")],
    [State("current-data-store", "children")],
    prevent_initial_call=True,
)
def export_csv(n_clicks, stored_data):
    """Export the current measurement data as CSV."""
    if not n_clicks or not stored_data:
        return None
    # Convert stored JSON back to DataFrame
    df = pd.read_json(stored_data, orient="records")

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"measurements_{timestamp}.csv"

    return dcc.send_data_frame(df.to_csv, filename, index=False)


def generate_stats(df):
    """Generate statistics content for the data."""
    if df.empty:
        return html.P("No data available for statistics.", className="text-muted")

    total_records = len(df)
    unique_sensors = df["sensor_id"].nunique() if "sensor_id" in df.columns else 0
    date_range = None

    if "date_time" in df.columns and not df["date_time"].isna().all():
        min_date = df["date_time"].min()
        max_date = df["date_time"].max()
        if isinstance(min_date, str):
            min_date = pd.to_datetime(min_date)
        if isinstance(max_date, str):
            max_date = pd.to_datetime(max_date)
        date_range = (
            f"{min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}"
        )

    soil_moisture_stats = None
    if "soil_moisture" in df.columns and not df["soil_moisture"].isna().all():
        soil_moisture_stats = {
            "mean": df["soil_moisture"].mean(),
            "std": df["soil_moisture"].std(),
            "min": df["soil_moisture"].min(),
            "max": df["soil_moisture"].max(),
        }

    stats_elements = [
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Strong("Total Records: "),
                        html.Span(f"{total_records:,}"),
                    ],
                    md=3,
                ),
                dbc.Col(
                    [
                        html.Strong("Unique Sensors: "),
                        html.Span(str(unique_sensors)),
                    ],
                    md=3,
                ),
                dbc.Col(
                    [
                        html.Strong("Date Range: "),
                        html.Span(date_range if date_range else "N/A"),
                    ],
                    md=6,
                ),
            ],
            className="mb-2",
        ),
    ]

    if soil_moisture_stats:
        stats_elements.append(
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Strong("Soil Moisture Stats: "),
                            html.Span(
                                f"Mean: {soil_moisture_stats['mean']:.3f}, "
                                f"Std: {soil_moisture_stats['std']:.3f}, "
                                f"Range: [{soil_moisture_stats['min']:.3f}, {soil_moisture_stats['max']:.3f}]"  # noqa
                            ),
                        ],
                        md=12,
                    ),
                ],
                className="mb-2",
            )
        )

    return html.Div(stats_elements)
