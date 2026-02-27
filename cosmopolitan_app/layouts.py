"""Collection of layout components for the web application."""

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html

from cosmopolitan_app.constants import (
    LOADING_OVERLAY_MODAL_SHARED_ID,
    NAVBAR_COLLAPSE_DIV_SHARED_ID,
    NAVBAR_TOGGLER_BUTTON_SHARED_ID,
    NEW_JOB_LINK_SHARED_ID,
    URL_LOCATION_SHARED_ID,
)
from cosmopolitan_app.error_handling import error_modal

loading_overlay = dbc.Modal(
    dbc.ModalBody(
        [dbc.Spinner(size="lg"), html.H4("Loading...", className="text-center mt-3")],
        className="text-center",
    ),
    id=LOADING_OVERLAY_MODAL_SHARED_ID,
    is_open=False,
    backdrop="static",  # Prevents closing by clicking outside
    keyboard=False,  # Prevents closing with escape key
    centered=True,
    size="sm",
)


def app_layout():
    """Create the main page layout with navbar and content."""
    return html.Div(
        className="d-flex flex-column min-vh-100 bg-light",
        children=[
            dcc.Location(id=URL_LOCATION_SHARED_ID, refresh=True),
            error_modal,
            create_navbar(),
            dash.page_container,
            loading_overlay,
        ],
    )


def create_navbar():
    """Create a navbar layout."""
    return html.Nav(
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
                    dbc.NavbarToggler(id=NAVBAR_TOGGLER_BUTTON_SHARED_ID),
                    dbc.Collapse(
                        dbc.Nav(
                            className="navbar-nav me-auto mb-2 mb-lg-0",
                            children=[
                                dbc.NavItem(
                                    dbc.NavLink(
                                        "New Job",
                                        href=dash.page_registry["pages.new_job"][
                                            "relative_path"
                                        ],
                                        id=NEW_JOB_LINK_SHARED_ID,  # testing  # noqa
                                    )
                                ),
                                dbc.NavItem(
                                    dbc.NavLink(
                                        "Documentation",
                                        href=dash.page_registry["pages.documentation"][
                                            "relative_path"
                                        ],
                                    )
                                ),
                                dbc.NavItem(
                                    dbc.NavLink(
                                        "Job Management",
                                        href=dash.page_registry["pages.job_management"][
                                            "relative_path"
                                        ],
                                    )
                                ),
                                dbc.NavItem(
                                    dbc.NavLink(
                                        "Worker Management",
                                        href=dash.page_registry[
                                            "pages.worker_management"
                                        ]["relative_path"],
                                    )
                                ),
                                dbc.NavItem(
                                    dbc.NavLink(
                                        "Logs",
                                        href=dash.page_registry["pages.logs"][
                                            "relative_path"
                                        ],
                                    )
                                ),
                                dbc.NavItem(
                                    dbc.NavLink(
                                        "Measurements",
                                        href=dash.page_registry[
                                            "pages.measurment_view"
                                        ]["relative_path"],
                                    )
                                ),
                                dbc.NavItem(
                                    dbc.NavLink(
                                        "Sensor Management",
                                        href=dash.page_registry[
                                            "pages.sensor_management"
                                        ]["relative_path"],
                                    )
                                ),
                                dbc.NavItem(
                                    dbc.NavLink(
                                        "CRNS Admin",
                                        href=dash.page_registry["pages.crns_db_admin"][
                                            "relative_path"
                                        ],
                                    )
                                ),
                            ],
                        ),
                        id=NAVBAR_COLLAPSE_DIV_SHARED_ID,
                        navbar=True,
                    ),
                ]
            )
        ],
    )


@callback(
    Output(NAVBAR_COLLAPSE_DIV_SHARED_ID, "is_open"),
    [Input(NAVBAR_TOGGLER_BUTTON_SHARED_ID, "n_clicks")],
    [State(NAVBAR_COLLAPSE_DIV_SHARED_ID, "is_open")],
)
def toggle_navbar_collapse(n_clicks, is_open):
    """Toggle the navbar collapse state."""
    if n_clicks:
        return not is_open
    return is_open


def create_header(title, subtitle, bg_color="bg-info", id="", rounded=True):
    """Create a header layout."""
    className = f"{bg_color} rounded-top py-2" if rounded else f"{bg_color} py-2"
    layout = html.Div(
        className=className,
        children=[
            html.H2(title, className="text-center", id=f"{id}-title"),  # nocheck
            (
                html.H3(
                    subtitle,
                    className="text-center",
                    id=f"{id}-subtitle",  # nocheck
                )
                if subtitle != ""
                else None
            ),
        ],
        id=id,
    )

    return layout


def landing_page_layout_column(
    header_title, header_id, job_id_store, job_id, main_content_id
):
    """Create a landing page layout for a given job ID."""
    header = create_header(
        header_title, "Loading ...", bg_color="bg-secondary", id=header_id
    )

    content = [
        dcc.Store(id=job_id_store, data=job_id),  # nocheck
        header,
        html.Div(
            html.Div(
                dbc.Spinner(
                    size="lg",
                    color="primary",
                    type="border",
                    fullscreen=False,
                ),
                className="d-flex justify-content-center align-items-center flex-grow-1",  # noqa
            ),
            id=main_content_id,  # nocheck
            className="flex-grow-1 d-flex flex-column",
        ),
    ]
    return page_container_column_layout(content)


def page_container_column_layout(content, main_content_id="main-content-container"):
    """Create a page container with a single column layout."""
    # Content layout
    class_names_content = "col-md-11 col-lg-10 col-xl-9 bg-white border border-dark rounded p-0 mb-4 mt-2 d-flex flex-column"  # noqa
    page = dbc.Row(
        dbc.Col(
            className=class_names_content,
            children=content,
            id=main_content_id,  # nocheck
        ),
        className="flex-grow-1 d-flex justify-content-center g-0",
    )
    return page


def landing_page_layout_fullscreen(
    header_title, header_id, job_id_store, job_id, main_content_id
):
    """Create a landing page layout for a given job ID."""
    header = create_header(
        header_title,
        "Loading ...",
        bg_color="bg-secondary",
        id=header_id,
        rounded=False,
    )

    content = [
        dcc.Store(id=job_id_store, data=job_id),  # nocheck
        header,
        html.Div(
            html.Div(
                dbc.Spinner(
                    size="lg",
                    color="primary",
                    type="border",
                    fullscreen=False,
                ),
                className="d-flex justify-content-center align-items-center flex-grow-1",  # noqa
            ),
            id=main_content_id,  # nocheck
            className="flex-grow-1 d-flex flex-column",
        ),
    ]

    return page_container_fullscreen_layout(content)


def page_container_fullscreen_layout(content):
    """Create a page container with a fullscreen layout."""
    return html.Div(
        className="d-flex flex-column flex-grow-1 bg-white p-0 m-0", children=content
    )
