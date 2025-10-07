"""Documentation page for the Cosmopolitan App."""

import dash
from dash import html

dash.register_page(
    __name__,
)

layout = html.Div("RED", style={"color": "red"}, className="flex-grow-1 bg-info")
