"""Collection of layout components for the web application."""

import dash_bootstrap_components as dbc
from dash import html


def create_navbar(page_registry):
    """Create a navbar layout."""
    return html.Nav(
        className="navbar navbar-expand-lg sticky-top navbar-dark bg-primary",
        children=[
            dbc.Container(
                children=[
                    dbc.NavbarBrand(
                        href=page_registry["pages.home"]["relative_path"],
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
                                        href=page_registry["pages.input"][
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


def create_header(title, subtitle, bg_color="bg-info", id=""):
    """Create a header layout."""
    layout = html.Div(
        className=f"{bg_color} rounded-top py-2",
        children=[
            html.H2(title, className="text-center"),
            html.H3(subtitle, className="text-center") if subtitle != "" else None,
        ],
        id=id,
    )

    return layout
