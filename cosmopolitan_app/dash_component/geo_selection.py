"""Interactive map with selection of area and stations."""

from datetime import datetime
from logging.config import dictConfig

import dash_bootstrap_components as dbc
import dash_leaflet as dl
from dash import Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate

from cosmopolitan_app.dash_component.dash_component import (
    Callback,
    list_callbacks,
    logging_config,
    stand_alone,
)

# from copy import deepcopy as copy


# Mock database

car1_markers = [
    [51.345196463050826, 12.414422035217287],
    [51.348279058081204, 12.419657707214357],
    [51.35066457624785, 12.423863410949709],
    [51.3518974920107, 12.426609992980959],
    [51.351441853093576, 12.428884506225588],
    [51.35130784078504, 12.432918548583986],
    [51.35101301232653, 12.436652183532717],
    [51.35095940694842, 12.44051456451416],
    [51.35074498480889, 12.44532108306885],
    [51.35154906265818, 12.44575023651123],
    [51.353130374597505, 12.444462776184084],
    [51.35532803953693, 12.444033622741701],
    [51.35709681523268, 12.444033622741701],
    [51.35961586271914, 12.443733215332033],
    [51.360714552809064, 12.443046569824219],
    [51.361866809223855, 12.437982559204102],
    [51.36293864963168, 12.434763908386232],
    [51.362751079371044, 12.431416511535646],
    [51.361116506013474, 12.43055820465088],
    [51.35905310880836, 12.430772781372072],
    [51.357498800184544, 12.431030273437502],
    [51.356185636281936, 12.432575225830078],
    [51.35546204008662, 12.43356227874756],
    [51.3546848314424, 12.43502140045166],
]
car2_markers = [
    [51.36339417420936, 12.404808998107912],
    [51.36264389602007, 12.406182289123535],
    [51.3617060309992, 12.406654357910158],
    [51.36052697343983, 12.40785598754883],
    [51.35977664828087, 12.408671379089355],
    [51.3588119264444, 12.407813072204592],
    [51.358463549676706, 12.407169342041017],
    [51.356614428634046, 12.406482696533205],
    [51.35465803090915, 12.406568527221681],
    [51.352487135647884, 12.405753135681152],
    [51.3505841675457, 12.405753135681152],
    [51.34937802008044, 12.405881881713867],
    [51.3474481180961, 12.406182289123535],
    [51.34592022138066, 12.40605354309082],
    [51.345598552423, 12.404165267944338],
    [51.34600063826727, 12.398371696472168],
    [51.34610786056325, 12.394895553588869],
]
train_markers = [
    [51.35045015272857, 12.395625114440918],
    [51.350396546691954, 12.40137577056885],
    [51.350155318751106, 12.406010627746582],
    [51.34978007276329, 12.4096155166626],
    [51.34905637539417, 12.4130916595459],
    [51.348037818992616, 12.416353225708008],
    [51.3467243838968, 12.420172691345217],
    [51.345571746574585, 12.423648834228517],
    [51.344579919161575, 12.429227828979494],
    [51.34444588678374, 12.433476448059084],
    [51.34693882485117, 12.434463500976564],
    [51.348332666595084, 12.434978485107422],
    [51.34986048287651, 12.43630886077881],
    [51.35267474794107, 12.43858337402344],
    [51.35773998946247, 12.440857887268066],
    [51.36033939330241, 12.441630363464357],
    [51.3623491405115, 12.443175315856934],
    [51.36449277366826, 12.443647384643556],
    [51.36628798923511, 12.442703247070314],
    [51.36942274916623, 12.43982791900635],
    [51.37081590691952, 12.435493469238281],
]

db_mock = [
    {
        "name": "car1",
        "dates": ["2021-01-02"],
        "markers": car1_markers,
        "station_type": 2,
    },
    {
        "name": "car2",
        "dates": ["2021-01-01"],
        "markers": car2_markers,
        "station_type": 2,
    },
    {
        "name": "train",
        "dates": ["2021-01-01", "2021-01-02", "2021-01-03", "2021-01-04", "2021-01-05"],
        "markers": train_markers,
        "station_type": 3,
    },
    {
        "name": "station1",
        "dates": ["2021-01-01", "2021-01-02", "2021-01-03", "2021-01-04", "2021-01-05"],
        "markers": [[51.35259383446255, 12.431545257568361]],
        "station_type": 1,
    },
    {
        "name": "station2",
        "dates": ["2021-01-01", "2021-01-02", "2021-01-03", "2021-01-04", "2021-01-05"],
        "markers": [[51.35299589236889, 12.43553638458252]],
        "station_type": 1,
    },
    {
        "name": "station3",
        "dates": ["2021-01-05"],
        "markers": [[51.3517897080651, 12.433862686157228]],
        "station_type": 1,
    },
    {
        "name": "station4",
        "dates": ["2021-01-01", "2021-01-05"],
        "markers": [[51.3517897080651, 12.433862686157228]],
        "station_type": 1,
    },
    {
        "name": "station5",
        "dates": ["2021-01-04", "2021-01-05"],
        "markers": [[51.356721461133915, 12.423734664916994]],
        "station_type": 1,
    },
]


def has_date_in_range(start_date_str, end_date_str, date_list):
    """Check if date is in range."""
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")

    for date_str in date_list:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        if start_date <= date <= end_date:
            return True
    return False


def is_inside_bounds(marker, lat_min, lat_max, lng_min, lng_max):
    """Check if marker is inside bounds."""
    lat, lng = marker
    return lat_min <= lat <= lat_max and lng_min <= lng <= lng_max


def construct_marker(station):
    """Construct marker."""
    if station["station_type"] == 1:
        return dl.Marker(position=station["markers"][0])
    if station["station_type"] == 2:
        return dl.Polyline(positions=station["markers"], color="red", weight=10)
    if station["station_type"] == 3:
        return dl.Polyline(positions=station["markers"], color="green", weight=10)


def get_stations(start_date_str, end_date_str, station_type_list, area_geojson):
    """Get the data."""
    if area_geojson is None:
        print("no area_geojson")
        return []
    try:
        bounds = area_geojson["features"][0]["properties"]["_bounds"]
        lat_min = min(bounds[0]["lat"], bounds[1]["lat"])
        lat_max = max(bounds[0]["lat"], bounds[1]["lat"])
        lng_min = min(bounds[0]["lng"], bounds[1]["lng"])
        lng_max = max(bounds[0]["lng"], bounds[1]["lng"])
    except IndexError:
        bounds = None
    station_list = []
    for station in db_mock:
        if (
            not has_date_in_range(start_date_str, end_date_str, station["dates"])
            or station["station_type"] not in station_type_list
        ):
            continue
        if bounds is None:
            station_list.append(station)
            continue
        if any(
            (
                is_inside_bounds(marker, lat_min, lat_max, lng_min, lng_max)
                for marker in station["markers"]
            )
        ):
            station_list.append(station)

    return [construct_marker(station) for station in station_list]


# Mock databas END

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
        html.P(
            "Select which subset of measurments you would like to use. "
            "Choose the time frame and the area of interest. "
            "Furthermore, choose the measurement stations (car, train, stationary)"
        ),
        dcc.DatePickerRange(
            clearable=True,
            start_date=datetime.strptime("2021-01-01", "%Y-%m-%d").date(),
            end_date=datetime.strptime("2021-01-05", "%Y-%m-%d").date(),
            id="date-picker",
        ),
        checklist,
    ],
    id="offcanvas",
    title="Choose CRN Measurements",
    placement="end",
    is_open=False,
)

double_selection_alert = html.Div(
    dbc.Alert(
        html.H3(
            "You can only select one area.",
        ),
        style={"zIndex": 1000},
        is_open=True,
        dismissable=True,
        color="danger",
        className="m-4 d-inline-block text-center",
    ),
    className="row justify-content-center",
)
# Only allow to draw one rectangle in dl.EditControl
main_map = html.Div(
    dl.Map(
        [
            html.Div(
                className="container",
                id="alert-container",
            ),
            dl.TileLayer(zIndex=1),
            # TODO icon
            dl.EasyButton(icon="fa-globe", title="So easy", id="open-offcanvas"),
            dl.FeatureGroup(
                [
                    dl.EditControl(
                        id="edit-control", position="topleft", draw=options_draw
                    )
                ]
            ),
            dl.LayerGroup(id="markers"),
        ],
        center=[51.352513937451086, 12.432832717895508],
        zoom=15,
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


class TurnOffDraw(Callback):
    """If the user selects a two areas, both are cleared."""

    in_out_state = (
        Output("alert-container", "children"),
        Output("edit-control", "editToolbar"),
        Input("edit-control", "geojson"),
    )
    parameters = {}

    @staticmethod
    def function(area_geojson):
        """If the user selects a two areas, both are cleared."""
        if area_geojson is None:
            raise PreventUpdate
        if len(area_geojson["features"]) < 2:
            raise PreventUpdate
        return double_selection_alert, {
            "mode": "remove",
            "action": "clear all",
            "n_clicks": 1,
        }


class SelectStationsArea(Callback):
    """Select date range."""

    in_out_state = (
        Output("markers", "children"),
        Input("edit-control", "geojson"),
        Input("date-picker", "start_date"),
        Input("date-picker", "end_date"),
        Input("station-input", "value"),
    )

    parameters = {}

    @staticmethod
    def function(area_geojson, start_date_str, end_date_str, station_type_list):
        """Select date range."""
        if area_geojson is None:
            raise PreventUpdate
        markers = get_stations(
            start_date_str, end_date_str, station_type_list, area_geojson
        )
        for marker in markers:
            print(marker)
        return markers
        return get_stations(
            start_date_str, end_date_str, station_type_list, area_geojson
        )


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
        """Open side menuse."""
        if n1:
            return not is_open
        return is_open


callbacks = list_callbacks(globals())
css_route = "/static/flatly_bootstrap.css"
base_path = "/results/"
if __name__ == "__main__":
    css_route = [
        dbc.themes.BOOTSTRAP,
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css",  # noqa
    ]
    dictConfig(logging_config)
    stand_alone(app_layout, callbacks, css_route)
