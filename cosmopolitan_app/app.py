"""Dash app with multiple pages."""

import dash
import dash_bootstrap_components as dbc
from dash import Dash, html

from cosmopolitan_app.layouts import create_navbar

# Initialize the Dash app
app = Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.FLATLY],
    suppress_callback_exceptions=True,
)


# Content layout
class_names_content = (
    "col-md-11 col-lg-10 col-xl-9 bg-white border border-dark rounded p-0"
)
content = html.Div(
    children=[
        html.Div(
            className="row justify-content-center pt-2",
            children=[
                html.Div(
                    className=class_names_content,
                    children=[
                        dash.page_container,
                    ],
                )
            ],
        )
    ]
)

# Main app layout
app.layout = html.Div(
    className="d-flex flex-column min-vh-100 bg-light",
    children=[
        create_navbar(dash.page_registry),
        content,
    ],
)

if __name__ == "__main__":
    app.run(debug=True)
