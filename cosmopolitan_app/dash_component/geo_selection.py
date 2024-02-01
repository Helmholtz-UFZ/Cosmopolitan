from datetime import date
from logging.config import dictConfig

from dash import html, Input, Output, State, dcc
import dash_leaflet as dl
import dash_bootstrap_components as dbc

from cosmopolitan_app.dash_component.dash_component import (
    Callback,
    list_callbacks,
    logging_config,
    stand_alone,
)

stationary_marker = [
    dl.Marker(position=[51.35259383446255, 12.431545257568361]),
    dl.Marker(position=[51.35299589236889, 12.43553638458252]),
    dl.Marker(position=[51.3517897080651, 12.433862686157228]),
    dl.Marker(position=[51.356721461133915, 12.423734664916994]),
    dl.Marker(position=[51.346964653301065, 12.425708770751955]),
    dl.Marker(position=[51.35881193536079, 12.436394691467287]),
    dl.Marker(position=[51.3517897080651, 12.441158294677736]),
]

options_draw = {
    "polyline": False,
    "polygon": False,
    "circlemarker": False,
    "circle": False,
    "marker": False,
    "rectangle": {"shapeOptions": {"clickable": False}},
}

checklist = html.Div(
    [
        dbc.Label("CRN Measurement Stations"),
        dbc.Checklist(
            options=[
                {"label": "Stationary", "value": 1},
                {"label": "Car", "value": 2},
                {"label": "Train", "value": 3},
            ],
            value=[1],
            id="station-input",
        ),
    ]
)

side_bar = dbc.Offcanvas(
    [
        dcc.DatePickerRange(
            clearable=True,
            start_date=date.today(),
        ),
        html.P(
            "This is the content of the Offcanvas. "
            "Close it by clicking on the close button, or "
            "the backdrop."
        ),
        checklist,
    ],
    id="offcanvas",
    title="Title",
    placement="end",
    is_open=False,
)

main_map = html.Div(
    dl.Map(
        [
            dl.TileLayer(),
            # TODO icon
            dl.EasyButton(icon="fa-globe", title="So easy", id="open-offcanvas"),
            dl.FeatureGroup(
                [
                    dl.EditControl(
                        id="edit_control", draw=options_draw, position="topleft"
                    )
                ]
            ),
            dl.LayerGroup(id="markers"),
        ],
        center=[51.3517897080651, 12.441158294677736],
        zoom=10,
        style={"height": "100%"},
        id="map",
    ),
    style={"height": "100vh"},
)

app_layout = html.Div(
    [
        side_bar,
        main_map,
        html.Div(id="hidden-div", style={"display": "none"}),
    ],
    style={"height": "100vh"},
)


class SelectStations(Callback):
    """Select stations."""

    in_out_state = (
        Output("markers", "children"),
        Input("station-input", "value"),
    )

    parameters = {
        "prevent_initial_call": True,
    }

    @staticmethod
    def function(options):
        if 1 in options:
            return stationary_marker


class ToggleOffcanvas(Callback):
    """Open side menuse."""

    in_out_state = (
        Output("offcanvas", "is_open"),
        Input("open-offcanvas", "n_clicks"),
        [State("offcanvas", "is_open")],
    )

    parameters = {
        "prevent_initial_call": True,
    }

    @staticmethod
    def function(n1, is_open):
        if n1:
            return not is_open
        return is_open


callbacks = list_callbacks(globals())
css_route = "/static/flatly_bootstrap.css"
base_path = "/results/"
if __name__ == "__main__":
    css_route = [
        dbc.themes.BOOTSTRAP,
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css",
    ]
    dictConfig(logging_config)
    stand_alone(app_layout, callbacks, css_route)
