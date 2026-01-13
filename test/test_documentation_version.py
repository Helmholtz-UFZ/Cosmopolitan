"""Test that documentation version matches application version."""

import tomllib
from pathlib import Path

import pytest


def test_documentation_version_matches_app_version():
    """Verify documentation version matches current app version.

    This test ensures documentation is regenerated after version bumps.
    If this test fails, run: python cosmopolitan_app/generate_docs.py
    """
    # Read app version from pyproject.toml
    project_root = Path(__file__).parent.parent
    pyproject_path = project_root / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)
    app_version = pyproject["tool"]["poetry"]["version"]

    # Read doc version from doc_version.txt
    version_file = (
        project_root / "cosmopolitan_app" / "assets" / "docs" / "doc_version.txt"
    )

    if not version_file.exists():
        pytest.fail(
            "Documentation has not been generated yet.\n"
            "See: cosmopolitan_app/doc_generator.py\n"
        )

    doc_version = version_file.read_text(encoding="utf-8").strip()

    # Compare versions
    if app_version != doc_version:
        pytest.fail(
            "Documentation is outdated!\n"
            f"  App version:     {app_version}\n"
            f"  Doc version:     {doc_version}\n"
            "See: cosmopolitan_app/generate_docs.py\n"
        )
