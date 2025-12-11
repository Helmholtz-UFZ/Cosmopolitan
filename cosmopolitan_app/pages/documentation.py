"""Documentation page for the Cosmopolitan App."""

from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import dcc

from cosmopolitan_app.layouts import create_header, page_container_column_layout

dash.register_page(__name__)


docs_file = Path(__file__).parent.parent / "assets" / "docs" / "documentation.md"
documentation_markdown = docs_file.read_text(encoding="utf-8")

# Page header
header = create_header(
    "Documentation",
    "User guide and reference for the COSMOPOLITAN webservice",
    bg_color="bg-info",
)

# Markdown content with HTML support for anchor links
markdown_content = dcc.Markdown(
    documentation_markdown,
    dangerously_allow_html=True,
)

# Layout
layout = page_container_column_layout(
    [
        header,
        dbc.Row(dbc.Col(markdown_content, className="col-11 col-xl-10 mx-auto my-4")),
    ]
)
