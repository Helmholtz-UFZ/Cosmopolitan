"""New interactive results page with TiTiler-based soil moisture maps."""

import json
import logging
import math
import os
import urllib.parse

import dash
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import matplotlib.pyplot as plt
from dash import Input, Output, State, callback, dcc, html
from dash_extensions.javascript import Namespace
from pyproj import Transformer
from soil_moisture_prediction.plot_functions import (
    SCALE_FILE_NAME,
    SOIL_MOISTURE_UNIT,
    SOIL_MOISTURE_VMAX,
    SOIL_MOISTURE_VMIN,
)

from cosmopolitan_app.config import JOB_WORK_DIR_TEMPLATE, TILESERVER_URL
from cosmopolitan_app.constants import (
    LOADING_OVERLAY_ID,
    RESULT_CONTAINER_ID,
    RESULTS_COLOR_BAR_INFO_ID,
    RESULTS_CURRENT_DATE_DISPLAY_ID,
    RESULTS_CURRENT_MAP_TYPE_BOX_ID,
    RESULTS_DATE_PAGINATION_ID,
    RESULTS_DATE_SELECTOR_ID,
    RESULTS_DUMMY_ID,
    RESULTS_HEADER_ID,
    RESULTS_JOB_ID_STORE,
    RESULTS_MAIN_CONTENT_ID,
    RESULTS_MAP_TYPE_SELECTOR_ID,
    RESULTS_MAP_TYPES_ID,
    RESULTS_MEASUREMENTS_SWITCH_ID,
    RESULTS_OPACITY_SLIDER_ID,
    RESULTS_PREVIOUS_MAP_TYPE_BOX_ID,
    RESULTS_PREVIOUS_MAP_TYPE_STORE_ID,
    RESULTS_SOIL_MOISTURE_MAP_ID,
    RESULTS_SWITCH_MAP_BUTTON_ID,
    RESULTS_TABS_ID,
    URL_ID,
)
from cosmopolitan_app.error_handling import NotFinishedException
from cosmopolitan_app.job import Job
from cosmopolitan_app.layouts import landing_page_layout_fullscreen
from cosmopolitan_app.utils import swap_classes

dash.register_page(
    __name__,
    path_template="/results/<job_id>",
    name="Results",
)

osm_layer = dl.TileLayer(
    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution="© OpenStreetMap contributors",
)


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
            "value": "prediction-geotiff",
            "label": "Soil Moisture",
            "time_dependent": True,
        },
        {
            "value": "prediction_distance-geotiff",
            "label": "Prediction Distance",
            "time_dependent": True,
        },
    ]

    for file in os.listdir(job_work_dir):
        if file.startswith("predictor_") and file.endswith(".tif"):
            predictor_name = file.replace("predictor_", "").replace(".tif", "")
            time_step = predictor_name.split("_")[-1]
            predictor_name = "_".join(predictor_name.split("_")[:-1])
            display_name = predictor_name.replace("_", " ").replace("-", " ").title()
            if time_step == "constant":
                time_dependent = False
            else:
                time_dependent = True

            map_types.append(
                {
                    "value": f"{predictor_name}-geotiff",
                    "label": display_name,
                    "time_dependent": time_dependent,
                }
            )

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


def create_controls(available_dates, available_map_types):
    """Create controls for selecting map type and date."""
    map_type_options = [
        {"label": map_type["label"], "value": map_type["value"]}
        for map_type in available_map_types
    ]
    init_map_type = "prediction-geotiff"

    # Map type selector dropdown
    map_type_selector = html.Div(
        [
            html.Label(
                "Select Map Type:",
                style={"fontWeight": "bold", "marginBottom": "5px"},
            ),
            dcc.Dropdown(
                id=RESULTS_MAP_TYPE_SELECTOR_ID,
                options=map_type_options,
                value=init_map_type,
                style={"marginBottom": "15px"},
            ),
        ],
        className="mb-3",
    )

    # Date selector with pagination
    date_selector = html.Div(
        [
            html.Label(
                "Select Date:",
                style={"fontWeight": "bold", "marginBottom": "5px"},
            ),
            html.Div(
                [
                    html.Strong("Current Date: "),
                    html.Span(
                        available_dates[0],
                        id=RESULTS_CURRENT_DATE_DISPLAY_ID,
                    ),
                ],
                className="mb-2",
            ),
            dbc.Pagination(
                id=RESULTS_DATE_PAGINATION_ID,
                max_value=len(available_dates),
                first_last=True,
                previous_next=True,
                fully_expanded=False,
                active_page=1,
            ),
        ],
        className="mb-3",
    )

    # Measurements overlay switch
    measurements_switch = html.Div(
        [
            dbc.Label(
                "Show Measurements Overlay", html_for=RESULTS_MEASUREMENTS_SWITCH_ID
            ),
            dbc.Switch(
                id=RESULTS_MEASUREMENTS_SWITCH_ID,
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
                style={"fontWeight": "bold", "marginBottom": "5px"},
            ),
            dcc.Slider(
                id=RESULTS_OPACITY_SLIDER_ID,
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
                                id=RESULTS_CURRENT_MAP_TYPE_BOX_ID,
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
                                id=RESULTS_PREVIOUS_MAP_TYPE_BOX_ID,
                                className="border rounded p-2 mb-2 bg-light",
                            ),
                        ],
                        className="mb-3",
                    ),
                    dbc.Button(
                        "Switch",
                        id=RESULTS_SWITCH_MAP_BUTTON_ID,
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
        id=RESULTS_PREVIOUS_MAP_TYPE_STORE_ID, data=previous_map_store_data
    )

    # Store for available dates
    dates_store = dcc.Store(id=RESULTS_DATE_SELECTOR_ID, data=available_dates)

    map_controls = dbc.Tab(
        [
            previous_map_store,
            dates_store,
            map_type_selector,
            date_selector,
            measurements_switch,
            opacity_slider,
            switch_card,
        ],
        label="Maps",
        className="m-3",
        labelClassName="mx-2 mt-2 bg-white border",
        activeLabelClassName="border-white",
    )

    plot_controls = dbc.Tab(
        ["Pass"],
        label="Stats",
        className="m-3",
        labelClassName="mx-2 mt-2 bg-white border",
        activeLabelClassName="border-white",
    )

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
        id=RESULTS_TABS_ID,
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


def create_tile_layer(job_id, map_type, date, color_bar_info, opacity=0.9):
    """Create TileLayer for GeoTIFF files using TiTiler."""
    # Remove -geotiff suffix for file naming
    base_map_type = map_type.replace("-geotiff", "")

    map_is_predictor = False
    if base_map_type == "prediction":
        tiff_filename = f"prediction_{date}.tif"
    elif base_map_type == "measurements":
        tiff_filename = f"measurements_{date}.tif"
    elif base_map_type == "prediction_distance":
        tiff_filename = f"prediction_distance_{date}.tif"
    else:
        map_is_predictor = True
        job_work_dir = JOB_WORK_DIR_TEMPLATE.format(job_id=job_id)
        time_dependent_file = f"predictor_{base_map_type}_{date}.tif"
        time_independent_file = f"predictor_{base_map_type}_constant.tif"

        if date and os.path.exists(os.path.join(job_work_dir, time_dependent_file)):
            tiff_filename = time_dependent_file
        else:
            tiff_filename = time_independent_file

    # TiTiler WebMercatorQuad format with proper URL encoding, maxzoom, and colormap
    file_path = f"file:///data/{job_id}/{tiff_filename}"
    encoded_url = urllib.parse.quote(file_path, safe=":/")

    tick_values = None
    # Add colormap and rescaling for soil moisture visualization
    if base_map_type == "prediction":
        # Use consistent soil moisture scale from soil-moisture-prediction library
        colormap_params = (
            f"&colormap_name=spectral&rescale={SOIL_MOISTURE_VMIN},{SOIL_MOISTURE_VMAX}"
        )
        vmin, vmax, unit = SOIL_MOISTURE_VMIN, SOIL_MOISTURE_VMAX, SOIL_MOISTURE_UNIT
        colormap = spectral_colorscale
    elif base_map_type == "prediction_distance":
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
    elif map_is_predictor:
        # Load predictor scale from metadata file
        vmin, vmax, unit = color_bar_info[base_map_type]
        colormap_params = f"&colormap_name=viridis&rescale={vmin},{vmax}"
        colormap = viridis_colorscale
    else:
        raise ValueError(f"Unknown map type for colormap: {map_type}")

    tile_url = f"{TILESERVER_URL}/cog/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}@1x?url={encoded_url}&maxzoom=15{colormap_params}"  # noqa
    logging.info(f"Using map URL: {tile_url}", extra={"tag": "frontend"})

    tile_layer = dl.TileLayer(id="map-tile-layer", url=tile_url, opacity=opacity)
    legend_layer = create_colorbar_legend(vmin, vmax, unit, colormap, tick_values)

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
        RESULTS_HEADER_ID,
        RESULTS_JOB_ID_STORE,
        job_id,
        RESULTS_MAIN_CONTENT_ID,
    )


default_map_layers = [osm_layer, dl.FullScreenControl()]
viridis_colorscale = get_viridis_colorscale()
rdbu_colorscale = get_rdbu_colorscale()
spectral_colorscale = get_spectral_colorscale()

# GeoJSON JavaScript callbacks - use Namespace to reference functions in
# assets/geojson_functions.js
geojson_ns = Namespace("dashExtensions", "default")


@callback(
    Output(LOADING_OVERLAY_ID, "is_open", allow_duplicate=True),
    Input(RESULTS_DATE_SELECTOR_ID, "value"),
    Input(RESULTS_DUMMY_ID, "data"),
    prevent_initial_call=True,
)
def show_loading(*inputs):
    """Show loading overlay when preparing input."""
    return any(input for input in inputs if input is not None)


@callback(
    [
        Output(RESULTS_HEADER_ID, "className", allow_duplicate=True),
        Output(f"{RESULTS_HEADER_ID}-subtitle", "children"),
        Output(RESULTS_MAIN_CONTENT_ID, "children"),
    ],
    [Input(RESULTS_JOB_ID_STORE, "data")],
    [State(RESULTS_HEADER_ID, "className")],
    prevent_initial_call="initial_duplicate",
)
def load_results_content(job_id, header_class_name):
    """Load results content for the given job ID."""
    logging.info(f"Loading results for job {job_id}", extra={"tag": "frontend"})
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

    controls = create_controls(available_dates, available_map_types)
    map_center, map_zoom = get_map_center_and_zoom(job)

    leaflet_map = dl.Map(
        id=RESULTS_SOIL_MOISTURE_MAP_ID,
        children=default_map_layers,
        className="flex-grow-1",
        center=map_center,
        zoom=map_zoom,
    )

    main_content = [
        dcc.Store(id=RESULTS_DUMMY_ID, data=None),
        dcc.Store(id=RESULTS_MAP_TYPES_ID, data=available_map_types),
        dcc.Store(id=RESULTS_COLOR_BAR_INFO_ID, data=color_bar_info),
        dbc.Row(
            [
                dbc.Col(
                    [
                        leaflet_map,
                        html.Div(id="dynamic-legend"),
                    ],
                    className="col-9 flex-grow-1 d-flex pe-0",
                    id=RESULT_CONTAINER_ID,
                ),
                dbc.Col(
                    controls,
                    className="col-3 p-0",
                    id="controls-container",
                ),
            ],
            className="flex-grow-1 d-flex",
        ),
    ]

    return header_class_name, header_subtitle, main_content


@callback(
    Output(RESULTS_SOIL_MOISTURE_MAP_ID, "children"),
    Output(RESULTS_CURRENT_DATE_DISPLAY_ID, "children"),
    Output(LOADING_OVERLAY_ID, "is_open", allow_duplicate=True),
    Input(RESULTS_DATE_PAGINATION_ID, "active_page"),
    Input(RESULTS_MAP_TYPE_SELECTOR_ID, "value"),
    Input(RESULTS_MEASUREMENTS_SWITCH_ID, "value"),
    Input(RESULTS_OPACITY_SLIDER_ID, "value"),
    State(RESULTS_JOB_ID_STORE, "data"),
    State(RESULTS_MAP_TYPES_ID, "data"),
    State(RESULTS_COLOR_BAR_INFO_ID, "data"),
    State(RESULTS_DATE_SELECTOR_ID, "data"),
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
        logging.warning(
            f"Invalid date index {date_index} for {len(available_dates)} dates",
            extra={"tag": "frontend"},
        )
        return dash.no_update, dash.no_update, False

    # Get the actual date string
    selected_date = available_dates[date_index]

    logging.info(
        f"Updating map for {job_id}, type {map_type}, date {selected_date} (page {page_index}), measurements: {show_measurements}, opacity: {opacity}",  # noqa
        extra={"tag": "frontend"},
    )

    # Create base map layers (returns [tile_layer, colorbar])
    if map_type.endswith("-geotiff"):
        new_map_layers = create_tile_layer(
            job_id, map_type, selected_date, color_bar_info, opacity
        )
    else:
        raise ValueError(f"Unknown map type: {map_type}")

    # Add measurements overlay if switch is enabled
    if show_measurements:
        # Get measurements layers (returns [geojson, colorbar])
        measurements_layers = create_geojson_layer(
            job_id, "measurements-geojson", selected_date
        )
        # Add only the GeoJSON layer (first element), not the colorbar
        # This ensures the map's colorbar (from new_map_layers) is kept
        new_map_layers = [new_map_layers[0], measurements_layers[0], new_map_layers[1]]

    return (default_map_layers + new_map_layers, selected_date, False)


@callback(
    Output(RESULTS_PREVIOUS_MAP_TYPE_STORE_ID, "data"),
    Output(RESULTS_CURRENT_MAP_TYPE_BOX_ID, "children"),
    Output(RESULTS_PREVIOUS_MAP_TYPE_BOX_ID, "children"),
    Output(RESULTS_SWITCH_MAP_BUTTON_ID, "disabled"),
    Input(RESULTS_MAP_TYPE_SELECTOR_ID, "value"),
    State(RESULTS_PREVIOUS_MAP_TYPE_STORE_ID, "data"),
    State(RESULTS_MAP_TYPES_ID, "data"),
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
    Output(RESULTS_MAP_TYPE_SELECTOR_ID, "value", allow_duplicate=True),
    Input(RESULTS_SWITCH_MAP_BUTTON_ID, "n_clicks"),
    State(RESULTS_PREVIOUS_MAP_TYPE_STORE_ID, "data"),
    prevent_initial_call=True,
)
def switch_maps(n_clicks, store):
    """Switch between current and previous map types."""
    if n_clicks and store and store.get("previous"):
        # Return the previous map type, which will trigger the dropdown change
        return store["previous"]
    return dash.no_update


@callback(
    Output(URL_ID, "pathname", allow_duplicate=True),
    Input(RESULTS_TABS_ID, "active_tab"),
    State(RESULTS_JOB_ID_STORE, "data"),
    prevent_initial_call=True,
)
def tab_content(active_tab, job_id):
    """Navigate to submission page when clicking the back tab."""
    if active_tab != "tab-2":
        return dash.no_update
    result_base_path = dash.page_registry["pages.submission"]["path_template"]
    result_path = result_base_path.replace("<job_id>", job_id)
    return result_path
