from dash import Dash, html, Input, Output
import dash_leaflet as dl

from logging.config import dictConfig
from cosmopolitan_app.dash_component.dash_component import (
    Callback,
    list_callbacks,
    logging_config,
    stand_alone,
)

options_draw = {
    "polyline": False,
    "polygon": False,
    "circlemarker": False,
    "circle": False,
    "marker": False,
    "rectangle": {"shapeOptions": {"clickable": False}},
}

app = Dash()
app_layout = html.Div(
    [
        dl.Map(
            children=[
                dl.TileLayer(),
                dl.FeatureGroup([dl.EditControl(id="edit_control", draw=options_draw)]),
            ],
            center=[51.80, 11.32],
            zoom=6,
            style={"height": "98%"},
            id="map",
        ),
        html.Div(id="hidden-div", style={"display": "none"}),
    ],
    style={"height": "100vh"},
)


class GetAreaa(Callback):
    """Get the selected area."""

    in_out_state = (Output("hidden-div", "children"), Input("edit_control", "geojson"), )

    parameters = {}

    @staticmethod
    def function(geojson):
        """Get the selected area."""
        print("Triggered")
        print(geojson)


callbacks = list_callbacks(globals())
css_route = "/static/flatly_bootstrap.css"
base_path = "/results/"
if __name__ == "__main__":
    dictConfig(logging_config)
    stand_alone(app_layout, callbacks, css_route)
