"""View and analyze your soil moisture prediction results.

This page provides comprehensive visualization and analysis tools for your completed
prediction job:

**Interactive Maps:**
- View soil moisture predictions overlaid on geographic maps
- Switch between different map types (OpenStreetMap, satellite imagery)
- Navigate through prediction time steps
- Toggle measurement point displays
- Adjust map opacity and explore spatial patterns

**Statistical Analysis:**
- Correlation heatmaps showing relationships between variables
- Feature importance plots revealing which predictors matter most
- Statistical summaries for each time step
- Detailed performance metrics

You can explore results across multiple time periods, examine which environmental
factors most influence soil moisture predictions, and understand model performance
through various visualization tools.

NOTE: This docstring is displayed on the documentation webpage.
"""

import json
import logging
import math
import os

import dash
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html
from dash_extensions.javascript import Namespace
from plotly.subplots import make_subplots
from pyproj import Transformer
from soil_moisture_prediction.plot_functions import (
    CONSTANT_TIME_STEP,
    SCALE_FILE_NAME,
    SOIL_MOISTURE_UNIT,
    SOIL_MOISTURE_VMAX,
    SOIL_MOISTURE_VMIN,
)

from cosmopolitan_app import map_utils
from cosmopolitan_app.config import JOB_WORK_DIR_TEMPLATE
from cosmopolitan_app.constants import (
    COLOR_BAR_INFO_STORE_RESULTS_ID,
    CORRELATION_FIGURE_GRAPH_RESULTS_ID,
    CORRELATION_GRAPH_RESULTS_ID,
    CURRENT_DATE_DISPLAY_DIV_RESULTS_ID,
    CURRENT_MAP_TYPE_BOX_DIV_RESULTS_ID,
    DATE_PAGINATION_MAP_BUTTON_RESULTS_ID,
    DATE_PAGINATION_STATS_BUTTON_RESULTS_ID,
    DATE_SELECTOR_DROPDOWN_RESULTS_ID,
    DUMMY_DIV_RESULTS_ID,
    HEADER_DIV_RESULTS_ID,
    IMPORTANCE_GRAPH_RESULTS_ID,
    IMPORTANCE_SELECTED_DIV_RESULTS_ID,
    JOB_STORE_RESULTS_ID,
    LOADING_OVERLAY_MODAL_SHARED_ID,
    MAIN_CONTENT_DIV_RESULTS_ID,
    MAP_TYPE_SELECTOR_DROPDOWN_RESULTS_ID,
    MAP_TYPES_STORE_RESULTS_ID,
    MEASUREMENTS_SWITCH_RESULTS_ID,
    OPACITY_SLIDER_RESULTS_ID,
    PREVIOUS_MAP_TYPE_BOX_DIV_RESULTS_ID,
    PREVIOUS_MAP_TYPE_STORE_RESULTS_ID,
    RESULT_CONTAINER_DIV_RESULTS_ID,
    SOIL_MOISTURE_MAP_GRAPH_RESULTS_ID,
    STATS_CONTAINER_DIV_RESULTS_ID,
    STATS_DATA_STORE_RESULTS_ID,
    STATS_VIEW_SELECTOR_DROPDOWN_RESULTS_ID,
    SWITCH_MAP_BUTTON_RESULTS_ID,
    TABS_RESULTS_ID,
    URL_LOCATION_SHARED_ID,
)
from cosmopolitan_app.error_handling import NotFinishedException
from cosmopolitan_app.files_route import create_download_button
from cosmopolitan_app.job import Job
from cosmopolitan_app.layouts import landing_page_layout_fullscreen
from cosmopolitan_app.utils import swap_classes

log = logging.getLogger(__name__)

dash.register_page(
    __name__,
    path_template="/results/<job_id>",
)

osm_layer = dl.TileLayer(
    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution="© OpenStreetMap contributors",
)


def create_date_selector(available_dates, type):
    """Create date selector with pagination."""
    if not available_dates:
        return html.Div("No available dates", className="mb-3")

    pagination_id = (
        DATE_PAGINATION_MAP_BUTTON_RESULTS_ID
        if type == "map"
        else DATE_PAGINATION_STATS_BUTTON_RESULTS_ID
    )

    date_selector = html.Div(
        [
            html.Label(
                "Select Date:",
                className="fw-bold mb-1",
            ),
            html.Div(
                [
                    html.Strong("Current Date: "),
                    html.Span(
                        available_dates[0],
                        id=CURRENT_DATE_DISPLAY_DIV_RESULTS_ID,
                    ),
                ],
                className="mb-2",
            ),
            dbc.Pagination(
                id=pagination_id,  # nocheck
                max_value=len(available_dates),
                first_last=True,
                previous_next=True,
                fully_expanded=False,
                active_page=1,
            ),
        ],
        className="mb-3",
    )

    return date_selector


def get_spectral_colorscale(n_colors=10):
    """Generate Spectral colorscale array for dl.Colorbar."""
    spectral = plt.get_cmap("Spectral")
    colors = [spectral(i / (n_colors - 1)) for i in range(n_colors)]
    return [
        f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
        for r, g, b, a in colors
    ]


def get_viridis_colorscale(n_colors=10):
    """Generate Spectral colorscale array for dl.Colorbar."""
    viridis = plt.get_cmap("viridis")
    colors = [viridis(i / (n_colors - 1)) for i in range(n_colors)]
    return [
        f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
        for r, g, b, a in colors
    ]


def get_rdbu_colorscale(n_colors=10):
    """Generate RdBu colorscale array for dl.Colorbar (red-white-blue divergent)."""
    rdbu = plt.get_cmap("RdBu")
    colors = [rdbu(i / (n_colors - 1)) for i in range(n_colors)]
    return [
        f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
        for r, g, b, a in colors
    ]


def get_available_dates(job_id):
    """Get available dates for the job based on actual files and model date range."""
    job_work_dir = JOB_WORK_DIR_TEMPLATE.format(job_id=job_id)
    dates = []

    for file in os.listdir(job_work_dir):
        if file.startswith("measurements_") and file.endswith(".geojson"):
            date_str = file.replace("measurements_", "").replace(".geojson", "")
            dates.append(date_str)

    return dates


def get_available_map_types(job_id):
    """Get available map types based on job model configuration."""
    job_work_dir = JOB_WORK_DIR_TEMPLATE.format(job_id=job_id)
    map_types = [
        {
            "value": "prediction",
            "label": "Soil Moisture",
            "time_dependent": True,
        },
        {
            "value": "prediction_distance",
            "label": "Prediction Distance",
            "time_dependent": True,
        },
    ]

    if any(
        f.startswith("dispersion_coefficient_") and f.endswith(".tif")
        for f in os.listdir(job_work_dir)
    ):
        map_types.append(
            {
                "value": "dispersion_coefficient",
                "label": "Dispersion Coefficient",
                "time_dependent": True,
            }
        )

    for file in os.listdir(job_work_dir):
        if file.startswith("predictor_") and file.endswith(".tif"):
            predictor_name = file.removeprefix("predictor_").removesuffix(".tif")
            time_step = predictor_name.split("_")[-1]
            predictor_name = "_".join(predictor_name.split("_")[:-1])
            display_name = predictor_name.replace("_", " ").replace("-", " ").title()
            if time_step == CONSTANT_TIME_STEP:
                time_dependent = False
            else:
                time_dependent = True

            map_info = {
                "value": predictor_name,
                "label": display_name,
                "time_dependent": time_dependent,
            }

            if map_info not in map_types:
                map_types.append(map_info)

    return map_types


def get_map_center_and_zoom(job):
    """Calculate map center and zoom level from job area of interest.

    Returns:
        tuple: (center [lat, lon], zoom_level)
    """
    x1, y1 = job.model.area_x1, job.model.area_y1
    x2, y2 = job.model.area_x2, job.model.area_y2
    projection = job.model.projection

    min_x, max_x = min(x1, x2), max(x1, x2)
    min_y, max_y = min(y1, y2), max(y1, y2)

    # Transform to WGS84 if needed
    if projection == "EPSG:4326":
        lon_min, lat_min = min_x, min_y
        lon_max, lat_max = max_x, max_y
    else:
        transformer = Transformer.from_crs(projection, "EPSG:4326", always_xy=True)
        lon_min, lat_min = transformer.transform(min_x, min_y)
        lon_max, lat_max = transformer.transform(max_x, max_y)
        lon_min, lon_max = min(lon_min, lon_max), max(lon_min, lon_max)
        lat_min, lat_max = min(lat_min, lat_max), max(lat_min, lat_max)

    # Calculate center
    center_lat = (lat_min + lat_max) / 2
    center_lon = (lon_min + lon_max) / 2

    # Calculate zoom level based on bounding box
    # Assume map viewport is approximately 1000x800 pixels
    lat_diff = lat_max - lat_min
    lon_diff = lon_max - lon_min

    # Leaflet zoom calculation: fit the larger dimension
    # Each zoom level doubles the map scale
    # At zoom 0, the world is 256 pixels wide
    # World width in degrees is 360, height is ~170 (Web Mercator)
    lat_zoom = math.log2(170 * 800 / (lat_diff * 256)) if lat_diff > 0 else 15
    lon_zoom = math.log2(360 * 1000 / (lon_diff * 256)) if lon_diff > 0 else 15

    # Use the smaller zoom to ensure everything fits
    zoom = int(min(lat_zoom, lon_zoom, 18))  # Cap at zoom 18

    # Ensure minimum zoom of 5
    zoom = max(5, zoom)

    return [center_lat, center_lon], zoom


def create_map_controls(available_dates, available_map_types, job_id):
    """Create controls for selecting map type and date."""
    map_type_options = [
        {"label": map_type["label"], "value": map_type["value"]}
        for map_type in available_map_types
    ]
    init_map_type = "prediction"

    # Map type selector dropdown
    map_type_selector = html.Div(
        [
            html.Label(
                "Select Map Type:",
                className="fw-bold mb-1",
            ),
            dcc.Dropdown(
                id=MAP_TYPE_SELECTOR_DROPDOWN_RESULTS_ID,
                options=map_type_options,
                value=init_map_type,
                className="mb-3",
            ),
        ],
        className="mb-3",
    )

    # Date selector with pagination
    date_selector = create_date_selector(available_dates, "map")

    # Measurements overlay switch
    measurements_switch = html.Div(
        [
            dbc.Label(
                "Show Measurements Overlay", html_for=MEASUREMENTS_SWITCH_RESULTS_ID
            ),
            dbc.Switch(
                id=MEASUREMENTS_SWITCH_RESULTS_ID,
                value=False,
                className="ms-2",
            ),
        ],
        className="mb-3 d-flex align-items-center",
    )

    # Opacity slider
    opacity_slider = html.Div(
        [
            html.Label(
                "Map Opacity:",
                className="fw-bold mb-1",
            ),
            dcc.Slider(
                id=OPACITY_SLIDER_RESULTS_ID,
                min=0,
                max=1,
                step=0.1,
                value=0.9,
                marks={0: "0%", 0.5: "50%", 1: "100%"},
                tooltip={"placement": "bottom", "always_visible": False},
            ),
        ],
        className="mb-3",
    )

    # Switch maps card
    switch_card = dbc.Card(
        [
            dbc.CardHeader("Switch Maps", className="fw-bold"),
            dbc.CardBody(
                [
                    html.Div(
                        [
                            html.Strong("Current:"),
                            html.Div(
                                "Soil Moisture",
                                id=CURRENT_MAP_TYPE_BOX_DIV_RESULTS_ID,
                                className="border rounded p-2 mb-2 bg-light",
                            ),
                        ],
                        className="mb-3",
                    ),
                    html.Div(
                        [
                            html.Strong("Previous:"),
                            html.Div(
                                "None",
                                id=PREVIOUS_MAP_TYPE_BOX_DIV_RESULTS_ID,
                                className="border rounded p-2 mb-2 bg-light",
                            ),
                        ],
                        className="mb-3",
                    ),
                    dbc.Button(
                        "Switch",
                        id=SWITCH_MAP_BUTTON_RESULTS_ID,
                        color="primary",
                        className="w-100",
                        disabled=True,
                    ),
                ]
            ),
        ],
        className="mb-3",
    )

    # Store for previous map type

    previous_map_store_data = {"current": init_map_type, "previous": None}
    previous_map_store = dcc.Store(
        id=PREVIOUS_MAP_TYPE_STORE_RESULTS_ID, data=previous_map_store_data
    )

    # Store for available dates
    dates_store = dcc.Store(id=DATE_SELECTOR_DROPDOWN_RESULTS_ID, data=available_dates)

    download_button = create_download_button(job_id)

    map_controls = dbc.Tab(
        [
            previous_map_store,
            dates_store,
            map_type_selector,
            date_selector,
            measurements_switch,
            opacity_slider,
            switch_card,
            download_button,
        ],
        label="Maps",
        className="m-3",
        labelClassName="mx-2 mt-2 bg-white border",
        activeLabelClassName="border-white",
    )
    return map_controls


def create_stats_controls(available_dates, job_id):
    """Create stats controls with view selector."""
    date_selector = create_date_selector(available_dates, "stats")

    # View selector radio buttons
    view_selector = html.Div(
        [
            html.Label(
                "Select View:",
                className="fw-bold mb-1",
            ),
            dbc.RadioItems(
                id=STATS_VIEW_SELECTOR_DROPDOWN_RESULTS_ID,
                className="btn-group",
                inputClassName="btn-check",
                labelClassName="btn btn-outline-primary",
                labelCheckedClassName="active",
                options=[
                    {"label": "Correlation", "value": "correlation"},
                    {"label": "Importance", "value": "importance"},
                ],
                value="correlation",
            ),
        ],
        className="mb-3",
    )

    download_button = create_download_button(job_id)

    plot_controls = dbc.Tab(
        [view_selector, date_selector, download_button],
        label="Stats",
        className="m-3",
        labelClassName="mx-2 mt-2 bg-white border",
        activeLabelClassName="border-white",
    )
    return plot_controls


def create_controls(available_dates, available_map_types, job_id):
    """Create map and stats controls in tabs."""
    map_controls = create_map_controls(available_dates, available_map_types, job_id)
    plot_controls = create_stats_controls(available_dates, job_id)

    back_to_submission = dbc.Tab(
        ["Back to submission page"],
        label="Back",
        className="m-3",
        labelClassName="mx-2 mt-2 bg-white border",
        activeLabelClassName="border-white",
    )

    controls = dbc.Tabs(
        [map_controls, plot_controls, back_to_submission],
        className="bg-light",
        id=TABS_RESULTS_ID,
    )

    return controls


def create_colorbar_legend(min, max, unit, colorscale, tick_values):
    """Create a colorbar component from dynamic legend data."""
    # Create unique ID based on whether tick_values is set to force recreation
    colorbar_id = (
        "colorbar-with-ticks" if tick_values is not None else "colorbar-no-ticks"
    )

    colorbar_params = {
        "id": colorbar_id,
        "colorscale": colorscale,
        "width": 20,
        "height": 200,
        "min": min,
        "max": max,
        "position": "bottomleft",
        "unit": unit,
    }

    if tick_values is not None:
        colorbar_params["tickValues"] = tick_values

    return dl.Colorbar(**colorbar_params)


def load_color_bar_info(job_id):
    """Load predictor scale from metadata file."""
    job_work_dir = JOB_WORK_DIR_TEMPLATE.format(job_id=job_id)
    scale_file = os.path.join(job_work_dir, SCALE_FILE_NAME)

    with open(scale_file, "r") as f:
        return json.load(f)


def load_stats_data(job_id):
    """Load statistics data from CSV files."""
    job_work_dir = JOB_WORK_DIR_TEMPLATE.format(job_id=job_id)

    # Load correlation matrix
    corr_file = os.path.join(job_work_dir, "correlation_matrix.csv")
    corr_df = pd.read_csv(corr_file)

    # Load predictor importance
    importance_file = os.path.join(job_work_dir, "predictor_importance.csv")
    timeseries_df = pd.read_csv(importance_file)

    return {
        "correlation": corr_df.to_dict("records"),
        "timeseries": timeseries_df.to_dict("records"),
    }


def create_correlation_heatmap(corr_data, timestep):
    """Create correlation matrix heatmap for a specific timestep."""
    corr_df = pd.DataFrame(corr_data)

    # Filter by timestep
    # if dataframe contains a CONSTANT_TIME_STEP column, use that for filtering
    if any(corr_df["time_step"] == CONSTANT_TIME_STEP):
        timestep_df = corr_df[corr_df["time_step"] == CONSTANT_TIME_STEP]
    else:
        # timestep is a string (date like "2025-11-19")
        timestep_df = corr_df[corr_df["time_step"] == timestep]

    # Set feature as index and drop time_step column
    timestep_df = timestep_df.drop(columns=["time_step"]).set_index("feature")

    fig = px.imshow(
        timestep_df,
        labels={"x": "", "y": "", "color": "Correlation coefficient"},
        color_continuous_scale="RdBu_r",
        aspect="auto",
        text_auto=".2f",
        range_color=[-1, 1],
    )
    fig.update_layout(title=f"Correlation Matrix - {timestep}")

    return fig


def create_importance_by_timestep(timeseries_data, timestep):
    """Create bar chart for single timestep importance."""
    timeseries_df = pd.DataFrame(timeseries_data)
    # timestep is a string (date like "2025-11-19")
    timestep_df = timeseries_df[timeseries_df["time_step"] == timestep][
        ["predictor", "importance", "5th_percentile", "95th_percentile"]
    ]

    fig = go.Figure(
        go.Bar(
            x=timestep_df["predictor"],
            y=timestep_df["importance"],
            marker_color="steelblue",
            error_y={
                "type": "data",
                "symmetric": False,
                "array": timestep_df["95th_percentile"] - timestep_df["importance"],
                "arrayminus": timestep_df["importance"] - timestep_df["5th_percentile"],
            },
        )
    )
    fig.update_layout(
        title=f"Feature Importance - {timestep}",
        xaxis_title="Predictors",
        yaxis_title="Importance",
        yaxis_range=[0, 1],
        height=IMPORTANCE_SINGLE_DAY_HEIGHT,
    )

    return fig


def create_importance_all_timesteps(timeseries_data):
    """Create small multiples plot for all timesteps."""
    timeseries_df = pd.DataFrame(timeseries_data)
    predictors = timeseries_df["predictor"].unique()

    fig = make_subplots(
        rows=len(predictors),
        cols=1,
        subplot_titles=predictors,
        vertical_spacing=0.05,
    )

    for i, predictor in enumerate(predictors, 1):
        df_pred = timeseries_df[timeseries_df["predictor"] == predictor]

        # Add line connecting the bars
        fig.add_trace(
            go.Scatter(
                x=df_pred["time_step"].astype(str),
                y=df_pred["importance"],
                mode="lines",
                line={"color": "lightgrey", "width": 2},
                showlegend=False,
            ),
            row=i,
            col=1,
        )

        # Add bars with error bars
        fig.add_trace(
            go.Bar(
                x=df_pred["time_step"].astype(str),
                y=df_pred["importance"],
                marker_color="steelblue",
                showlegend=False,
                error_y={
                    "type": "data",
                    "symmetric": False,
                    "array": df_pred["95th_percentile"] - df_pred["importance"],
                    "arrayminus": df_pred["importance"] - df_pred["5th_percentile"],
                },
            ),
            row=i,
            col=1,
        )
        fig.update_yaxes(title_text="Importance", range=[0, 1], row=i, col=1)

    fig.update_layout(
        title="Feature Importance Over Time", height=IMPORTANCE_ALL_DAYS_HEIGHT
    )
    fig.update_xaxes(title_text="Time Steps", row=len(predictors), col=1)

    return fig


def _get_tile_params(job_id, map_type, date, color_bar_info):
    """Get parameters for tile layer and legend creation.

    Returns:
        tuple: (tiff_filename, vmin, vmax, unit, colormap, colormap_params, tick_values)
    """
    map_is_predictor = False
    if map_type == "prediction":
        tiff_filename = f"prediction_{date}.tif"
    elif map_type == "measurements":
        tiff_filename = f"measurements_{date}.tif"
    elif map_type == "prediction_distance":
        tiff_filename = f"prediction_distance_{date}.tif"
    elif map_type == "dispersion_coefficient":
        tiff_filename = f"dispersion_coefficient_{date}.tif"
    else:
        map_is_predictor = True
        job_work_dir = JOB_WORK_DIR_TEMPLATE.format(job_id=job_id)
        time_dependent_file = f"predictor_{map_type}_{date}.tif"
        time_independent_file = f"predictor_{map_type}_constant.tif"

        if date and os.path.exists(os.path.join(job_work_dir, time_dependent_file)):
            tiff_filename = time_dependent_file
        else:
            tiff_filename = time_independent_file

    tick_values = None
    # Add colormap and rescaling for soil moisture visualization
    if map_type == "prediction":
        # Use consistent soil moisture scale from soil-moisture-prediction library
        colormap_params = (
            f"&colormap_name=spectral&rescale={SOIL_MOISTURE_VMIN},{SOIL_MOISTURE_VMAX}"
        )
        vmin, vmax, unit = SOIL_MOISTURE_VMIN, SOIL_MOISTURE_VMAX, SOIL_MOISTURE_UNIT
        colormap = spectral_colorscale
    elif map_type == "prediction_distance":
        # Use balanced red-white-blue scale for prediction distance
        original_vmin, original_vmax, unit = color_bar_info[
            f"prediction_distance_{date}"
        ]
        # Create symmetric scale around zero
        max_abs = max(abs(original_vmin), abs(original_vmax))
        vmin, vmax = -max_abs, max_abs
        colormap_params = f"&colormap_name=rdbu&rescale={vmin},{vmax}"
        colormap = rdbu_colorscale
        if max_abs <= 1:
            tick_values = [vmin, 0, vmax]
        else:
            tick_values = [vmin, -1, 0, 1, vmax]
    elif map_type == "dispersion_coefficient":
        vmin, vmax, unit = color_bar_info[f"dispersion_coefficient_{date}"]
        colormap_params = f"&colormap_name=viridis&rescale={vmin},{vmax}"
        colormap = viridis_colorscale
    elif map_is_predictor:
        # Load predictor scale from metadata file
        vmin, vmax, unit = color_bar_info[map_type]
        colormap_params = f"&colormap_name=viridis&rescale={vmin},{vmax}"
        colormap = viridis_colorscale
    else:
        raise ValueError(f"Unknown map type for colormap: {map_type}")

    return tiff_filename, vmin, vmax, unit, colormap, colormap_params, tick_values


def create_tile_layer(job_id, map_type, date, color_bar_info, opacity=0.9):
    """Create TileLayer and legend for GeoTIFF files using TiTiler."""
    tiff_filename, vmin, vmax, unit, colormap, colormap_params, tick_values = (
        _get_tile_params(job_id, map_type, date, color_bar_info)
    )

    tile_layer = map_utils.create_tile_layer_component(
        job_id, tiff_filename, colormap_params, opacity
    )
    legend_layer = create_colorbar_legend(vmin, vmax, unit, colormap, tick_values)

    # Handle None tile_layer (e.g., when mocked in tests to avoid tile server
    # dependency)
    if tile_layer is None:
        return [legend_layer]
    return [tile_layer, legend_layer]


def create_geojson_layer(job_id, map_type, selected_date):
    """Create GeoJSON layer for measurement points using URL-based dl.GeoJSON."""
    # Construct GeoJSON URL
    geojson_url = f"/pictures/{job_id}/measurements_{selected_date}.geojson"

    # Create GeoJSON layer with viridis colorscale
    # Use Namespace to reference JavaScript callbacks in assets/geojson_functions.js
    geojson = dl.GeoJSON(
        url=geojson_url,
        pointToLayer=geojson_ns("geojsonPointToLayer"),
        onEachFeature=geojson_ns("geojsonOnEachFeature"),
        hideout={
            "colorProp": "soil_moisture",
            "circleOptions": {
                "fillOpacity": 1,
                "stroke": True,
                "radius": 5,  # Fallback radius
                "color": "black",
                "weight": 1,
            },
            "min": SOIL_MOISTURE_VMIN,
            "max": SOIL_MOISTURE_VMAX,
            "colorscale": spectral_colorscale,
        },
    )

    # Create colorbar legend using viridis colorscale
    legend_layer = create_colorbar_legend(
        SOIL_MOISTURE_VMIN,
        SOIL_MOISTURE_VMAX,
        SOIL_MOISTURE_UNIT,
        spectral_colorscale,
        None,
    )

    return [geojson, legend_layer]


def layout(job_id):
    """Layout for results page."""
    return landing_page_layout_fullscreen(
        "Results",
        HEADER_DIV_RESULTS_ID,
        JOB_STORE_RESULTS_ID,
        job_id,
        MAIN_CONTENT_DIV_RESULTS_ID,
    )


default_map_layers = [osm_layer, dl.FullScreenControl()]
viridis_colorscale = get_viridis_colorscale()
rdbu_colorscale = get_rdbu_colorscale()
spectral_colorscale = get_spectral_colorscale()

# GeoJSON JavaScript callbacks - use Namespace to reference functions in
# assets/geojson_functions.js
geojson_ns = Namespace("dashExtensions", "default")

# Container CSS classes for tab switching
CONTAINER_BASE_CLASSES = "col-9 flex-grow-1 pe-0"
CONTAINER_VISIBLE_CLASSES = f"{CONTAINER_BASE_CLASSES} d-flex"
CONTAINER_HIDDEN_CLASSES = f"{CONTAINER_BASE_CLASSES} d-none"

# Plot heights for predictor importance
IMPORTANCE_SINGLE_DAY_HEIGHT = 500
IMPORTANCE_ALL_DAYS_HEIGHT = 1700


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
    Input(DATE_SELECTOR_DROPDOWN_RESULTS_ID, "value"),
    Input(DUMMY_DIV_RESULTS_ID, "data"),
    prevent_initial_call=True,
)


@callback(
    [
        Output(HEADER_DIV_RESULTS_ID, "className", allow_duplicate=True),
        Output(f"{HEADER_DIV_RESULTS_ID}-subtitle", "children"),
        Output(MAIN_CONTENT_DIV_RESULTS_ID, "children"),
    ],
    [Input(JOB_STORE_RESULTS_ID, "data")],
    [State(HEADER_DIV_RESULTS_ID, "className")],
    prevent_initial_call="initial_duplicate",
)
def load_results_content(job_id, header_class_name):
    """Load results content for the given job ID."""
    log.info(f"Loading results for job {job_id}", extra={"tag": "frontend"})
    job = Job(job_id)

    if job.status != "COMPLETED":
        raise NotFinishedException(job_id)

    # Create the header with job information
    header_class_name = swap_classes(job.status_color(), header_class_name)
    header_subtitle = job.job_id

    # Get available dates and map types
    available_dates = get_available_dates(job_id)
    available_map_types = get_available_map_types(job_id)
    color_bar_info = load_color_bar_info(job_id)
    stats_data = load_stats_data(job_id)

    controls = create_controls(available_dates, available_map_types, job_id)
    map_center, map_zoom = get_map_center_and_zoom(job)

    leaflet_map = dl.Map(
        id=SOIL_MOISTURE_MAP_GRAPH_RESULTS_ID,
        children=default_map_layers,
        className="flex-grow-1",
        center=map_center,
        zoom=map_zoom,
    )

    # Map container (initially visible)
    map_container = dbc.Col(
        [
            leaflet_map,
            html.Div(),
        ],
        className=CONTAINER_VISIBLE_CLASSES,
        id=RESULT_CONTAINER_DIV_RESULTS_ID,
    )

    # Create plots
    correlation_fig = create_correlation_heatmap(
        stats_data["correlation"], available_dates[0]
    )
    importance_all_fig = create_importance_all_timesteps(stats_data["timeseries"])
    importance_selected_fig = create_importance_by_timestep(
        stats_data["timeseries"], available_dates[0]
    )

    # Stats container (initially hidden)
    stats_container = dbc.Col(
        [
            # Correlation graph container (initially visible)
            html.Div(
                dcc.Graph(
                    id=CORRELATION_FIGURE_GRAPH_RESULTS_ID,
                    figure=correlation_fig,
                ),
                id=CORRELATION_GRAPH_RESULTS_ID,
                className="d-block flex-grow-1",
            ),
            # Importance graphs container (initially hidden)
            html.Div(
                [
                    dcc.Graph(
                        id=IMPORTANCE_SELECTED_DIV_RESULTS_ID,
                        figure=importance_selected_fig,
                        # Bootstrap has no utility for exact chart height
                        style={"height": f"{IMPORTANCE_SINGLE_DAY_HEIGHT}px"},
                    ),
                    html.Div(
                        dcc.Graph(
                            figure=importance_all_fig,
                            # Bootstrap has no utility for exact chart height
                            style={"height": f"{IMPORTANCE_ALL_DAYS_HEIGHT}px"},
                        ),
                        className="overflow-auto",
                        # no Bootstrap class for calc() height  # noqa
                        style={
                            "height": f"calc(100% - {IMPORTANCE_SINGLE_DAY_HEIGHT}px)",
                            "maxHeight": f"{IMPORTANCE_ALL_DAYS_HEIGHT}px",
                        },
                    ),
                ],
                id=IMPORTANCE_GRAPH_RESULTS_ID,
                className="d-none flex-grow-1",
            ),
        ],
        className=CONTAINER_HIDDEN_CLASSES,
        id=STATS_CONTAINER_DIV_RESULTS_ID,
    )

    main_content = [
        dcc.Store(id=DUMMY_DIV_RESULTS_ID, data=None),
        dcc.Store(id=MAP_TYPES_STORE_RESULTS_ID, data=available_map_types),
        dcc.Store(id=COLOR_BAR_INFO_STORE_RESULTS_ID, data=color_bar_info),
        dcc.Store(id=STATS_DATA_STORE_RESULTS_ID, data=stats_data),
        dbc.Row(
            [
                map_container,
                stats_container,
                dbc.Col(
                    controls,
                    className="col-3 p-0",
                ),
            ],
            className="flex-grow-1 d-flex",
        ),
    ]

    return header_class_name, header_subtitle, main_content


@callback(
    Output(SOIL_MOISTURE_MAP_GRAPH_RESULTS_ID, "children"),
    Output(CURRENT_DATE_DISPLAY_DIV_RESULTS_ID, "children"),
    Output(LOADING_OVERLAY_MODAL_SHARED_ID, "is_open", allow_duplicate=True),
    Input(DATE_PAGINATION_MAP_BUTTON_RESULTS_ID, "active_page"),
    Input(MAP_TYPE_SELECTOR_DROPDOWN_RESULTS_ID, "value"),
    Input(MEASUREMENTS_SWITCH_RESULTS_ID, "value"),
    Input(OPACITY_SLIDER_RESULTS_ID, "value"),
    State(JOB_STORE_RESULTS_ID, "data"),
    State(MAP_TYPES_STORE_RESULTS_ID, "data"),
    State(COLOR_BAR_INFO_STORE_RESULTS_ID, "data"),
    State(DATE_SELECTOR_DROPDOWN_RESULTS_ID, "data"),
    prevent_initial_call=True,
)
def update_map(
    page_index,
    map_type,
    show_measurements,
    opacity,
    job_id,
    available_map_types,
    color_bar_info,
    available_dates,
):
    """Update map with selected map type and date from pagination."""
    if not job_id or not map_type or page_index is None:
        return dash.no_update, dash.no_update, False

    # Convert pagination page (1-indexed) to date array index (0-indexed)
    date_index = page_index - 1

    # Validate index
    if date_index < 0 or date_index >= len(available_dates):
        log.warning(
            f"Invalid date index {date_index} for {len(available_dates)} dates",
            extra={"tag": "frontend"},
        )
        return dash.no_update, dash.no_update, False

    # Get the actual date string
    selected_date = available_dates[date_index]

    log.info(
        f"Updating map for {job_id}, type {map_type}, date {selected_date} (page {page_index}), measurements: {show_measurements}, opacity: {opacity}",  # noqa
        extra={"tag": "frontend"},
    )

    # Create base map layers (returns [tile_layer, colorbar])
    new_map_layers = create_tile_layer(
        job_id, map_type, selected_date, color_bar_info, opacity
    )

    # Add measurements overlay if switch is enabled
    if show_measurements:
        # Get measurements layers (returns [geojson, colorbar])
        measurements_layers = create_geojson_layer(
            job_id, "measurements-geojson", selected_date
        )
        # Add only the GeoJSON layer (first element), not the colorbar
        # This ensures the map's colorbar (from new_map_layers) is kept
        new_map_layers = [new_map_layers[0], measurements_layers[0], new_map_layers[1]]

    return default_map_layers + new_map_layers, selected_date, False


@callback(
    Output(PREVIOUS_MAP_TYPE_STORE_RESULTS_ID, "data"),
    Output(CURRENT_MAP_TYPE_BOX_DIV_RESULTS_ID, "children"),
    Output(PREVIOUS_MAP_TYPE_BOX_DIV_RESULTS_ID, "children"),
    Output(SWITCH_MAP_BUTTON_RESULTS_ID, "disabled"),
    Input(MAP_TYPE_SELECTOR_DROPDOWN_RESULTS_ID, "value"),
    State(PREVIOUS_MAP_TYPE_STORE_RESULTS_ID, "data"),
    State(MAP_TYPES_STORE_RESULTS_ID, "data"),
    prevent_initial_call=True,
)
def track_map_type_changes(current_map_type, previous_store, available_map_types):
    """Track map type changes and update the switch maps card."""
    # previous_store contains: {"current": "...", "previous": "..."}
    # or None on first load

    if previous_store is None:
        # First time - initialize with current selection
        new_store = {"current": current_map_type, "previous": None}
    else:
        # Update: move current to previous, new selection to current
        new_store = {"current": current_map_type, "previous": previous_store["current"]}

    # Get display labels
    current_label = next(
        (mt["label"] for mt in available_map_types if mt["value"] == current_map_type),
        current_map_type,
    )

    previous_label = "None"
    button_disabled = True

    if new_store["previous"] is not None:
        previous_label = next(
            (
                mt["label"]
                for mt in available_map_types
                if mt["value"] == new_store["previous"]
            ),
            new_store["previous"],
        )
        button_disabled = False

    return new_store, current_label, previous_label, button_disabled


@callback(
    Output(MAP_TYPE_SELECTOR_DROPDOWN_RESULTS_ID, "value", allow_duplicate=True),
    Input(SWITCH_MAP_BUTTON_RESULTS_ID, "n_clicks"),
    State(PREVIOUS_MAP_TYPE_STORE_RESULTS_ID, "data"),
    prevent_initial_call=True,
)
def switch_maps(n_clicks, store):
    """Switch between current and previous map types."""
    if n_clicks and store and "previous" in store:
        # Return the previous map type, which will trigger the dropdown change
        return store["previous"]
    return dash.no_update


@callback(
    Output(RESULT_CONTAINER_DIV_RESULTS_ID, "className"),
    Output(STATS_CONTAINER_DIV_RESULTS_ID, "className"),
    Output(URL_LOCATION_SHARED_ID, "pathname", allow_duplicate=True),
    Input(TABS_RESULTS_ID, "active_tab"),
    State(JOB_STORE_RESULTS_ID, "data"),
    prevent_initial_call=True,
)
def tab_content(active_tab, job_id):
    """Switch between map and stats views, or navigate to submission page."""
    # tab-0: Maps
    if active_tab == "tab-0":
        return (
            CONTAINER_VISIBLE_CLASSES,  # Show map
            CONTAINER_HIDDEN_CLASSES,  # Hide stats
            dash.no_update,
        )
    # tab-1: Stats
    elif active_tab == "tab-1":
        return (
            CONTAINER_HIDDEN_CLASSES,  # Hide map
            CONTAINER_VISIBLE_CLASSES,  # Show stats
            dash.no_update,
        )
    # tab-2: Back to submission
    elif active_tab == "tab-2":
        result_base_path = dash.page_registry["pages.submission"]["path_template"]
        result_path = result_base_path.replace("<job_id>", job_id)
        return (
            dash.no_update,
            dash.no_update,
            result_path,
        )
    raise ValueError(f"Unknown active tab: {active_tab}")


@callback(
    Output(CORRELATION_GRAPH_RESULTS_ID, "className"),
    Output(IMPORTANCE_GRAPH_RESULTS_ID, "className"),
    Input(STATS_VIEW_SELECTOR_DROPDOWN_RESULTS_ID, "value"),
    prevent_initial_call=True,
)
def toggle_stats_view(view_type):
    """Toggle between correlation and importance views."""
    if view_type == "correlation":
        return "d-block flex-grow-1", "d-none"
    elif view_type == "importance":
        return "d-none", "d-block flex-grow-1"
    return dash.no_update, dash.no_update


@callback(
    Output(CORRELATION_FIGURE_GRAPH_RESULTS_ID, "figure"),
    Output(IMPORTANCE_SELECTED_DIV_RESULTS_ID, "figure"),
    Output(CURRENT_DATE_DISPLAY_DIV_RESULTS_ID, "children", allow_duplicate=True),
    Input(DATE_PAGINATION_STATS_BUTTON_RESULTS_ID, "active_page"),
    State(STATS_DATA_STORE_RESULTS_ID, "data"),
    State(DATE_SELECTOR_DROPDOWN_RESULTS_ID, "data"),
    prevent_initial_call=True,
)
def update_stats_plots_by_timestep(page_index, stats_data, available_dates):
    """Update correlation and importance plots for selected timestep."""
    if page_index is None or not stats_data:
        return dash.no_update, dash.no_update, dash.no_update

    # Convert pagination page (1-indexed) to date array index (0-indexed)
    date_index = page_index - 1

    # Get the actual date string
    selected_date = available_dates[date_index]

    # Create updated figures
    correlation_fig = create_correlation_heatmap(
        stats_data["correlation"], selected_date
    )
    importance_fig = create_importance_by_timestep(
        stats_data["timeseries"], selected_date
    )

    return correlation_fig, importance_fig, selected_date
