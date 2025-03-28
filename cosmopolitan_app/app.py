"""Dash app with multiple pages."""

import dash
import dash_bootstrap_components as dbc
from dash import Dash, html

# Initialize the Dash app
app = Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.FLATLY],
    suppress_callback_exceptions=True,
)


nav_bar = html.Nav(
    className="navbar navbar-expand-lg sticky-top navbar-dark bg-primary",
    children=[
        dbc.Container(
            children=[
                dbc.NavbarBrand(
                    href=dash.page_registry["pages.home"]["relative_path"],
                    children=[
                        html.Img(
                            src="/static/icon_white.svg",
                            width="30",
                            height="30",
                            className="d-inline-block align-text-top",
                            alt="Cosmopolitan Icon",
                        ),
                        " Cosmopolitan",
                    ],
                ),
                dbc.NavbarToggler(id="navbar-toggler"),
                dbc.Collapse(
                    dbc.Nav(
                        className="navbar-nav me-auto mb-2 mb-lg-0",
                        children=[
                            dbc.NavItem(
                                dbc.NavLink(
                                    "Input",
                                    href=dash.page_registry["pages.input"][
                                        "relative_path"
                                    ],
                                )
                            ),  # Update with appropriate link
                            dbc.NavItem(
                                dbc.NavLink("Documentation", href="/documentation")
                            ),  # Update with appropriate link
                        ],
                    ),
                    id="navbar-collapse",
                    navbar=True,
                ),
                dbc.Form(
                    className="d-flex",
                    action="/search_submission",  # Update with appropriate endpoint
                    method="post",
                    children=[
                        dbc.Input(
                            className="form-control me-2",
                            size=40,
                            name="job_id",
                            type="search",
                            placeholder="job_id",
                        ),
                        dbc.Button("Search", color="success", type="submit"),
                    ],
                ),
            ]
        )
    ],
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
        nav_bar,
        content,
    ],
)

if __name__ == "__main__":
    app.run(debug=True)
