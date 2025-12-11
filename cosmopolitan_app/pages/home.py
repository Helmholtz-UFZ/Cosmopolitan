"""Welcome to COSMOPOLITAN - the landing page for soil moisture prediction services.

This is the home page where you start your journey. COSMOPOLITAN (COSmic ray based
soil MOisture PredictiOn LIve Tree ANalysis) is a web service that analyzes cosmic
ray neutron sensor data to predict soil moisture content using machine learning models.

From here, you can begin creating a new prediction job to analyze soil moisture data
for your area of interest.

NOTE: This docstring is displayed on the documentation webpage.
"""

import dash
import dash_bootstrap_components as dbc
from dash import html

from cosmopolitan_app.layouts import create_header, page_container_column_layout

dash.register_page(__name__, path="/")

subtitle = [
    "To The Cosmopolitan Webservice \n some more text",
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


page_layout = [
    header,
    dbc.Row(
        dbc.Col(
            html.Img(
                src="/static/start_banner.png",
                style={"height": "70vh"},
                className="rounded mx-auto d-block m-3",
                alt="Welcome",
            ),
            className="text-center",
        ),
    ),
]

layout = page_container_column_layout(page_layout)
