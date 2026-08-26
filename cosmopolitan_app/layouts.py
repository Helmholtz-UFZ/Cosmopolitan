"""Collection of layout components for the web application.

The navbar-collapse callback is NOT defined here. `cosmo_suite.layouts` registers an
identical one at import time on the same shared ID, and two callbacks writing one
Output without allow_duplicate is a hard Dash error that takes the whole callback
registry down — not just the navbar. This app's IDs match the framework's by value,
so the framework's callback drives the navbar rendered below. The import is explicit
so that stays true no matter which framework page happens to be imported.

Framework MR on the list: register cosmo_suite.layouts' global callbacks behind an
opt-in function instead of at import time, so a consumer can own its own navbar.
"""

import cosmo_suite.layouts  # noqa: F401 — registers the navbar-collapse callback

# The column container comes from the framework: its version is a strict superset,
# and with wrapper_class left at None (this app's shell has no second panel to
# select against) the rendered DOM is identical to the copy that used to live here.
from cosmo_suite.layouts import page_container_column_layout  # noqa: F401
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html

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
                                        [
                                            html.I(className="bi bi-plus-circle me-1"),
                                            "New Job",
                                        ],
                                        href=dash.page_registry["pages.new_job"][
                                            "relative_path"
                                        ],
                                        id=NEW_JOB_LINK_SHARED_ID,  # testing  # noqa
                                    )
                                ),
                                dbc.NavItem(
                                    dbc.NavLink(
                                        [
                                            html.I(className="bi bi-book me-1"),
                                            "Documentation",
                                        ],
                                        href=dash.page_registry["pages.documentation"][
                                            "relative_path"
                                        ],
                                    )
                                ),
                                dbc.NavItem(
                                    dbc.NavLink(
                                        [
                                            html.I(className="bi bi-list-task me-1"),
                                            "Job Management",
                                        ],
                                        href=dash.page_registry["pages.job_management"][
                                            "relative_path"
                                        ],
                                    )
                                ),
                                dbc.NavItem(
                                    dbc.NavLink(
                                        [
                                            html.I(className="bi bi-cpu me-1"),
                                            "Worker Management",
                                        ],
                                        href=dash.page_registry[
                                            "pages.worker_management"
                                        ]["relative_path"],
                                    )
                                ),
                                dbc.NavItem(
                                    dbc.NavLink(
                                        [
                                            html.I(className="bi bi-journal-text me-1"),
                                            "Logs",
                                        ],
                                        href=dash.page_registry["pages.logs"][
                                            "relative_path"
                                        ],
                                    )
                                ),
                                dbc.NavItem(
                                    dbc.NavLink(
                                        [
                                            html.I(className="bi bi-graph-up me-1"),
                                            "Measurements",
                                        ],
                                        href=dash.page_registry[
                                            "pages.measurement_view"
                                        ]["relative_path"],
                                    )
                                ),
                                dbc.NavItem(
                                    dbc.NavLink(
                                        [
                                            html.I(
                                                className="bi bi-broadcast-pin me-1"
                                            ),
                                            "Sensor Management",
                                        ],
                                        href=dash.page_registry[
                                            "pages.sensor_management"
                                        ]["relative_path"],
                                    )
                                ),
                                dbc.NavItem(
                                    dbc.NavLink(
                                        [
                                            html.I(
                                                className="bi bi-database-gear me-1"
                                            ),
                                            "CRNS Admin",
                                        ],
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
