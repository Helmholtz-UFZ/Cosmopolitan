"""New interactive results page with TiTiler-based soil moisture maps."""

import json
import logging
import os
from datetime import datetime

import dash
import dash_leaflet as dl
from dash import Input, Output, callback, dcc, html

from cosmopolitan_app.config import JOB_WORK_DIR_TEMPLATE
from cosmopolitan_app.job import Job
from cosmopolitan_app.utils import InvalidJobID, JobNotFound

dash.register_page(
    __name__,
    path_template="/new_results/<job_id>",
    name="New Results",
)

TILESERVER_BASE_URL = "http://localhost:8000"


def get_available_dates(job_id):
    """Get available soil moisture dates for the job."""
    job_work_dir = JOB_WORK_DIR_TEMPLATE.format(job_id=job_id)
    dates = []

    if os.path.exists(job_work_dir):
        for file in os.listdir(job_work_dir):
            if file.startswith("soil_moisture_") and file.endswith(".tif"):
                # Extract date from filename: soil_moisture_20220327.tif
                date_str = file.replace("soil_moisture_", "").replace(".tif", "")
                try:
                    date_obj = datetime.strptime(date_str, "%Y%m%d")
                    dates.append(
                        {
                            "date": date_str,
                            "label": date_obj.strftime("%Y-%m-%d"),
                            "file": file,
                        }
                    )
                except ValueError:
                    continue

    return sorted(dates, key=lambda x: x["date"])


def load_color_scheme(job_id):
    """Load color scheme from metadata file."""
    job_work_dir = JOB_WORK_DIR_TEMPLATE.format(job_id=job_id)
    color_file = os.path.join(job_work_dir, "soil_moisture_colors.json")

    if os.path.exists(color_file):
        with open(color_file, "r") as f:
            return json.load(f)

    # Default color scheme if file not found
    return {
        "color_scheme": {
            "type": "linear",
            "stops": [
                {"value": 0.1, "color": "#d7191c", "label": "Very Dry"},
                {"value": 0.2, "color": "#fdae61", "label": "Dry"},
                {"value": 0.3, "color": "#ffffbf", "label": "Moderate"},
                {"value": 0.4, "color": "#abd9e9", "label": "Moist"},
                {"value": 0.45, "color": "#2c7bb6", "label": "Very Moist"},
            ],
        }
    }


def create_legend(color_scheme):
    """Create a legend component from color scheme."""
    stops = color_scheme["color_scheme"]["stops"]

    legend_items = []
    for stop in stops:
        legend_items.append(
            html.Div(
                [
                    html.Div(
                        style={
                            "width": "20px",
                            "height": "20px",
                            "backgroundColor": stop["color"],
                            "border": "1px solid #333",
                            "display": "inline-block",
                            "marginRight": "8px",
                        }
                    ),
                    html.Span(
                        f"{stop['label']} ({stop['value']})",
                        style={"fontSize": "12px", "verticalAlign": "top"},
                    ),
                ],
                style={
                    "marginBottom": "4px",
                    "display": "flex",
                    "alignItems": "center",
                },
            )
        )

    return html.Div(
        [
            html.H6(
                "Soil Moisture", style={"marginBottom": "10px", "fontWeight": "bold"}
            ),
            html.Div(legend_items),
        ],
        style={
            "position": "absolute",
            "bottom": "20px",
            "right": "20px",
            "backgroundColor": "white",
            "padding": "15px",
            "borderRadius": "5px",
            "boxShadow": "0 2px 5px rgba(0,0,0,0.2)",
            "zIndex": "1000",
            "fontSize": "12px",
        },
    )


def layout(job_id):
    """Layout for the new interactive results page with tile layers."""
    logging.info(
        f"Create new tile-based result page for job {job_id}", extra={"tag": "frontend"}
    )

    try:
        Job(job_id)
    except (JobNotFound, InvalidJobID):
        logging.info(f"Job {job_id} not found", extra={"tag": "job_submission"})
        return html.Div(
            [
                html.H1("Error", className="text-center mt-5"),
                html.P(
                    "The job you are looking for does not exist.",
                    className="text-center",
                ),
            ]
        )

    # Get available dates and color scheme
    available_dates = get_available_dates(job_id)
    color_scheme = load_color_scheme(job_id)

    if not available_dates:
        return html.Div(
            [
                html.H1("No Data", className="text-center mt-5"),
                html.P(
                    "No soil moisture data found for this job.", className="text-center"
                ),
            ]
        )

    # Create time slider
    date_options = [
        {"label": date["label"], "value": date["date"]} for date in available_dates
    ]

    controls = html.Div(
        [
            html.Div(
                [
                    html.Label(
                        "Select Date:",
                        style={"fontWeight": "bold", "marginBottom": "5px"},
                    ),
                    dcc.Dropdown(
                        id="date-selector",
                        options=date_options,
                        value=available_dates[0]["date"],
                        style={"width": "200px"},
                    ),
                ]
            )
        ],
        style={
            "position": "absolute",
            "top": "20px",
            "left": "20px",
            "zIndex": "1000",
            "backgroundColor": "white",
            "padding": "15px",
            "borderRadius": "5px",
            "boxShadow": "0 2px 5px rgba(0,0,0,0.2)",
        },
    )

    # Create map - center on the actual data extent
    # WGS84 bounds from TiTiler: [10.923, 51.791, 10.945, 51.805]
    # This is near Göttingen, Germany (very small 1.5km area)
    leaflet_map = dl.Map(
        id="soil-moisture-map",
        children=[
            dl.TileLayer(
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                attribution="© OpenStreetMap contributors",
            ),
        ],
        style={"width": "100vw", "height": "100vh"},
        center=[51.798, 10.934],  # Exact center of the data
        zoom=15,  # Very high zoom to see the tiny 1.5km grid
    )

    return html.Div(
        [
            leaflet_map,
            controls,
            create_legend(color_scheme),
            dcc.Store(id="job-data", data={"job_id": job_id, "dates": available_dates}),
            dcc.Store(id="color-scheme", data=color_scheme),
        ],
        style={
            "margin": "0",
            "padding": "0",
            "position": "fixed",
            "top": "0",
            "left": "0",
            "width": "100%",
            "height": "100%",
            "overflow": "hidden",
        },
    )


@callback(
    Output("soil-moisture-map", "children"),
    [Input("date-selector", "value"), Input("job-data", "data")],
    prevent_initial_call=False,
)
def update_map_tiles(selected_date, job_data):
    """Update map with soil moisture tiles for selected date."""
    if not selected_date or not job_data:
        # Return base map only
        return [
            dl.TileLayer(
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                attribution="© OpenStreetMap contributors",
            ),
        ]

    job_id = job_data["job_id"]

    # Build TiTiler URL for the selected date
    tif_path = f"/data/{job_id}/soil_moisture_{selected_date}.tif"
    tile_url = f"{TILESERVER_BASE_URL}/cog/tiles/{{z}}/{{x}}/{{y}}.png?url={tif_path}&rescale=0.1,0.45"  # noqa

    logging.info(
        f"Loading tiles for job {job_id}, date {selected_date}",
        extra={"tag": "frontend"},
    )
    logging.info(f"Tile URL template: {tile_url}", extra={"tag": "frontend"})

    # Use TileLayer for scalable tile-based rendering
    tile_url = f"{TILESERVER_BASE_URL}/cog/tiles/{{z}}/{{x}}/{{y}}.png?url={tif_path}&rescale=0.1,0.45"  # noqa

    return [
        dl.TileLayer(
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            attribution="© OpenStreetMap contributors",
        ),
        dl.TileLayer(
            url=tile_url,
            opacity=1,
            id="soil-moisture-tiles",
            attribution="Soil Moisture Data",
        ),
    ]


@callback(
    Output("date-selector", "options"),
    Input("job-data", "data"),
)
def update_date_options(job_data):
    """Update date selector options."""
    if not job_data or "dates" not in job_data:
        return []

    return [
        {"label": date["label"], "value": date["date"]} for date in job_data["dates"]
    ]
