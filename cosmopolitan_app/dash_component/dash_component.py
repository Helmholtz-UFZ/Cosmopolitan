"""Module that extends dash main class to be added to be served by flask."""


import dash
import dash_bootstrap_components as dbc
from flask import render_template
from markupsafe import Markup


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


def init_callbacks(dash_app, globals_module):
    """Add callbacks to dash app."""
    for callback in globals_module.values():
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
    app = dash.Dash()
    app.layout = app_layout

    init_callbacks(app, callbacks)
    app.run_server(debug=True)


def init_dash(server, globals_module, app_layout):
    """Add server to flask server.

    Usage:
    from dash_component import init_dash

    with app.app_context():
        from cosmopolitan_app.dash_component import some_component
        app = init_dash(app, some_component.globals_module(), some_component.app_layout)
    """
    dash_app = DashComponent(
        server=server,
        url_base_pathname="/results/",
        external_stylesheets=[dbc.themes.FLATLY]
        # routes_pathname_prefix="/results/",
    )
    dash_app.layout = app_layout
    init_callbacks(dash_app, globals_module)
    return dash_app.server
