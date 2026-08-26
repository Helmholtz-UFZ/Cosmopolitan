"""Test that the checked-in user documentation still matches its sources."""

import difflib

import pytest

from cosmopolitan_app.doc_generator import (
    DOCUMENTATION_FILE,
    DocumentationGenerator,
    without_timestamp,
)

REGENERATE_HINT = (
    "Regenerate with:\n"
    "  uv run python -m cosmopolitan_app.doc_generator --markdown-only\n"
    "(text only — no dev stack and no job IDs needed. Screenshots need the full\n"
    "invocation with both job IDs against a running dev stack.)"
)


def test_documentation_matches_page_docstrings():
    """Verify documentation.md is what the current page docstrings generate.

    documentation.md is a pure function of the page docstrings and the templates in
    doc_generator, apart from its generation timestamp. Regenerating and comparing
    therefore catches exactly the staleness that matters — a docstring or template
    edited without regenerating the docs — and stays quiet for changes that cannot
    affect the documentation, a version bump among them.

    The screenshots are not covered: they need a browser and a running dev stack.
    """
    if not DOCUMENTATION_FILE.exists():
        pytest.fail(f"Documentation has not been generated yet.\n{REGENERATE_HINT}")

    checked_in = without_timestamp(DOCUMENTATION_FILE.read_text(encoding="utf-8"))
    regenerated = without_timestamp(
        DocumentationGenerator().generate_full_documentation()
    )

    if checked_in != regenerated:
        diff = "\n".join(
            difflib.unified_diff(
                checked_in.splitlines(),
                regenerated.splitlines(),
                fromfile="documentation.md (checked in)",
                tofile="documentation.md (regenerated from the docstrings)",
                lineterm="",
            )
        )
        pytest.fail(f"Documentation is outdated!\n{REGENERATE_HINT}\n\n{diff}")
