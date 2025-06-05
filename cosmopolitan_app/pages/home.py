"""Landing page of the web application."""

import dash
import dash_bootstrap_components as dbc
from dash import html

from cosmopolitan_app.layouts import create_header

dash.register_page(__name__, path="/")

subtitle = [
    "To The Cosmopolitan Webservice ",
    html.Br(),
    html.Strong("COS"),
    html.Small("mic ray based soil "),
    html.Strong("MO"),
    html.Small("isture "),
    html.Strong("P"),
    html.Small("redicti"),
    html.Strong("O"),
    html.Small("n "),
    html.Strong("LI"),
    html.Small("ve "),
    html.Strong("T"),
    html.Small("ree "),
    html.Strong("AN"),
    html.Small("alysis"),
]
header = create_header(
    "Welcome",
    subtitle,
)

layout = [
    header,
    dbc.Row(
        dbc.Col(
            html.Img(
                src="/static/start_banner.png",
                style={"width": "40%"},
                className="rounded mx-auto d-block m-3",
                alt="Welcome",
            ),
            className="text-center",
        )
    ),
]
