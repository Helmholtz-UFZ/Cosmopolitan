"""Module that extends dash main class to be added to be served by flask."""

import logging
from logging.config import dictConfig

import dash
import dash_bootstrap_components as dbc
from dash_dangerously_set_inner_html import DangerouslySetInnerHTML
from flask import render_template
from markupsafe import Markup

from cosmopolitan_app.logger import ExcludeDebugMatplotLibFilter
from cosmopolitan_app.utils import error_response_args


class DashComponent(dash.Dash):
    """Class extends dash main class to be added to be served by flask."""

    def interpolate_index(
        self,
        metas="",
        title="",  # noqa: ARG002
        css="",
        config="",
        scripts="",
        app_entry="",
        favicon="",  # noqa: ARG002
        renderer="",
    ):
        """Build custom route based on template."""
        # markupsafe.Markup is used to
        # prevent Jinja from
        # escaping the Dash-rendered markup
        return render_template(
            "html/results/results.html",
            metas=Markup(metas),
            css=Markup(css),
            # config is mapped to dash_config
            # to avoid shadowing the global Flask config
            # in the Jinja environment
            dash_config=Markup(config),
            scripts=Markup(scripts),
            app_entry=Markup(app_entry),
            renderer=Markup(renderer),
        )


class Callback:
    """Identifier class for init_callbacks()."""

    pass


def list_callbacks(globals_module):
    """Add callbacks to dash app."""
    return [
        callback
        for callback in globals_module.values()
        if (
            isinstance(callback, type)
            and issubclass(callback, Callback)
            and callback is not Callback
        )
    ]


def init_callbacks(dash_app, callbacks):
    """Add callbacks to dash app."""
    for callback in callbacks:
        if (
            isinstance(callback, type)
            and issubclass(callback, Callback)
            and callback is not Callback
        ):
            dash_app.callback(*callback.in_out_state, **callback.parameters)(
                callback.function
            )

    return dash_app


def stand_alone(app_layout, callbacks):
    """For testing and devolpment."""
    app = dash.Dash(external_stylesheets=[dbc.themes.FLATLY])
    app.layout = app_layout

    init_callbacks(app, callbacks)
    app.run_server(debug=True)


def init_dash(server, globals_module, app_layout):
    """Add server to flask server.

    Usage:
    from dash_component import init_dash
    from cosmopolitan_app.dash_component import some_component

    app = init_dash(app, some_component.callbacks, some_component.app_layout)
    """
    dash_app = DashComponent(
        server=server,
        url_base_pathname="/results/",
        external_stylesheets=[dbc.themes.FLATLY],
    )
    dash_app.layout = app_layout
    init_callbacks(dash_app, globals_module)
    return dash_app.server


def error_response_dash(e):
    """Handle standard errors on flask site."""
    template_kwargs, html_error_code, log_it = error_response_args(e)
    logging.info(f"Dash handle { e.__class__.__name__ }")
    return DangerouslySetInnerHTML(
        render_template(
            template_kwargs["error_page"],
            **{k: v for k, v in template_kwargs.items() if k != "error_page"},
        )
    )


logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
        },
    },
    "handlers": {
        "default": {
            "level": "DEBUG",
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",  # Default is stderr
            "filters": ["exclude_debug_matplotlib"],
        },
    },
    "root": {
        "handlers": ["default"],
        "level": "DEBUG",
        "filters": ["exclude_debug_matplotlib"],
    },
    "filters": {"exclude_debug_matplotlib": {"()": ExcludeDebugMatplotLibFilter}},
}

dictConfig(logging_config)
