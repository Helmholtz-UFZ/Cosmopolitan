"""Collection of layout components for the web application."""

import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, html

from cosmopolitan_app.constants import (
    LOADING_OVERLAY_ID,
    NAVBAR_COLLAPSE_ID,
    NAVBAR_TOGGLER_ID,
    NEW_JOB_LINK_ID,
)

loading_overlay = dbc.Modal(
    dbc.ModalBody(
        [dbc.Spinner(size="lg"), html.H4("Loading...", className="text-center mt-3")],
        className="text-center",
    ),
    id=LOADING_OVERLAY_ID,
    is_open=False,
    backdrop="static",  # Prevents closing by clicking outside
    keyboard=False,  # Prevents closing with escape key
    centered=True,
    size="sm",
)


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
                    dbc.NavbarToggler(id=NAVBAR_TOGGLER_ID),
                    dbc.Collapse(
                        dbc.Nav(
                            className="navbar-nav me-auto mb-2 mb-lg-0",
                            children=[
                                dbc.NavItem(
                                    dbc.NavLink(
                                        "New Job",
                                        href=page_registry["pages.new_job"][
                                            "relative_path"
                                        ],
                                        id=NEW_JOB_LINK_ID,  # Id used for testing
                                    )
                                ),
                                dbc.NavItem(
                                    dbc.NavLink("Documentation", href="/documentation")
                                ),
                                dbc.NavItem(
                                    dbc.NavLink(
                                        "Job Management",
                                        href=page_registry["pages.job_management"][
                                            "relative_path"
                                        ],
                                    )
                                ),
                                dbc.NavItem(
                                    dbc.NavLink(
                                        "Logs",
                                        href=page_registry["pages.logs"][
                                            "relative_path"
                                        ],
                                    )
                                ),
                                dbc.NavItem(
                                    dbc.NavLink(
                                        "Measurments",
                                        href=page_registry["pages.measurment_view"][
                                            "relative_path"
                                        ],
                                    )
                                ),
                                dbc.NavItem(
                                    dbc.NavLink(
                                        "Sensor Management",
                                        href=page_registry["pages.sensor_management"][
                                            "relative_path"
                                        ],
                                    )
                                ),
                            ],
                        ),
                        id=NAVBAR_COLLAPSE_ID,
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


def register_navbar_callbacks(app):
    """Register callbacks for the navbar."""

    @callback(
        Output(NAVBAR_COLLAPSE_ID, "is_open"),
        [Input(NAVBAR_TOGGLER_ID, "n_clicks")],
        [State(NAVBAR_COLLAPSE_ID, "is_open")],
    )
    def toggle_navbar_collapse(n_clicks, is_open):
        """Toggle the navbar collapse state."""
        if n_clicks:
            return not is_open
        return is_open


def create_header(title, subtitle, bg_color="bg-info", id=""):
    """Create a header layout."""
    layout = html.Div(
        className=f"{bg_color} rounded-top py-2",
        children=[
            html.H2(title, className="text-center", id=f"{id}-title"),
            (
                html.H3(subtitle, className="text-center", id=f"{id}-subtitle")
                if subtitle != ""
                else None
            ),
        ],
        id=id,
    )

    return layout
