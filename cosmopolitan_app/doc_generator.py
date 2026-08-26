"""Documentation generator for COSMOPOLITAN webservice.

This module dynamically generates user-facing documentation by extracting docstrings
from page modules and formatting them as markdown.

The generated documentation.md is checked in, and test_documentation.py asserts that
it still matches the docstrings it was generated from. So an edit to a page docstring
or to a template here must be followed by

    uv run python -m cosmopolitan_app.doc_generator --markdown-only

which rewrites the markdown without touching the screenshots — no browser, no dev
stack, no job IDs.
"""

import argparse
import ast
import logging
import re
import sys
import tomllib
from datetime import datetime
from pathlib import Path

from cosmopolitan_app.screenshot_generator import ScreenshotGenerator

log = logging.getLogger(__name__)

INTRO_TEMPLATE = """# COSMOPOLITAN Webservice Documentation

### COSmic ray based soil MOisture PredictiOn LIve Tree ANalysis

*Last updated: {timestamp}*

## Table of Contents
1. [Introduction](#introduction)
2. [User Workflow](#user-workflow)
3. [Administration](#administration)

---

<h2 id="introduction">Introduction</h2>

COSMOPOLITAN is a web service for analyzing cosmic ray neutron sensor (CRNS) data to
predict soil moisture content using machine learning models. The service provides tools
for submitting prediction jobs, monitoring their execution, and analyzing results
through interactive visualizations.

### How It Works

The application uses a distributed architecture to handle prediction jobs efficiently:

- **Background Processing**: Prediction jobs are processed asynchronously by Celery
  workers, allowing you to submit jobs and navigate away while processing continues.
  You can check back anytime to monitor progress and view results.

- **Database**: Job data, sensor measurements, and system logs are stored in PostgreSQL
  with PostGIS extension for spatial data queries. This enables efficient geographic
  searches and spatial analysis.

- **Object Storage**: Large result files, including prediction maps and analysis data,
  are stored in MinIO object storage for efficient retrieval and long-term archival.

- **Web Interface**: Built with the Dash framework for interactive data visualization,
  providing real-time updates, interactive maps, and responsive charts.

---

"""

WORKFLOW_TEMPLATE = """<h2 id="user-workflow">User Workflow</h2>

This section describes the typical user journey for creating and analyzing soil moisture
predictions.

"""

ADMIN_TEMPLATE = """<h2 id="administration">Administration</h2>

Administrative pages for system management, monitoring, and configuration.

"""

FOOTER_TEMPLATE = "*Generated automatically from module docstrings*"

DOCS_DIR = Path(__file__).parent / "assets" / "docs"
DOCUMENTATION_FILE = DOCS_DIR / "documentation.md"
SCREENSHOTS_DIR = DOCS_DIR / "screenshots"

# The generated markdown is a pure function of the page docstrings and the templates
# above — except for this one line. Anything asking "is the checked-in file still
# current?" has to neutralise it first; see without_timestamp.
TIMESTAMP_LINE_PATTERN = re.compile(r"^\*Last updated: .*\*$", re.MULTILINE)
TIMESTAMP_PLACEHOLDER = "*Last updated: <generated>*"

# Page organization
USER_WORKFLOW_PAGES = [
    ("home", "Home Page"),
    ("new_job", "Create New Job"),
    ("input", "Job Input Form"),
    ("submission", "Job Submission"),
    ("results", "View Results"),
]

ADMIN_PAGES = [
    ("job_management", "Job Management"),
    ("sensor_management", "Sensor Management"),
    ("measurement_view", "Measurement Database"),
    ("crns_db_admin", "CRNS Database Administration"),
    ("logs", "Application Logs"),
    ("worker_management", "Worker Management"),
]

EXCLUDED_PAGES = ["documentation", "__init__"]

# Section markers some page docstrings use to separate user-facing prose from
# developer notes (see pages/worker_management.py).
USER_DOC_MARKER = "# User documentation"
DEVELOPER_NOTES_MARKER = "# Notes"


def without_timestamp(markdown: str) -> str:
    """Replace the generation timestamp with a fixed placeholder.

    Args:
        markdown: Generated or checked-in documentation markdown

    Returns:
        The markdown with its timestamp line neutralised, so two generations of the
        same sources compare equal.
    """
    return TIMESTAMP_LINE_PATTERN.sub(TIMESTAMP_PLACEHOLDER, markdown)


def clean_docstring(docstring: str) -> str:
    """Strip everything from a page docstring that is not user documentation.

    Drops NOTE: lines, the section markers themselves, and every line after the
    developer-notes marker — the marker's own text promises that section will not
    appear in the user documentation.
    """
    lines = []
    for line in docstring.split("\n"):
        stripped = line.strip()
        if stripped.startswith(DEVELOPER_NOTES_MARKER):
            break
        if stripped.startswith("NOTE:") or stripped.startswith(USER_DOC_MARKER):
            continue
        lines.append(line)

    return "\n".join(lines).strip()


def get_app_version() -> str:
    """Read application version from pyproject.toml using tomllib.

    Returns:
        Version string (e.g., "0.0.60")
    """
    project_root = Path(__file__).parent.parent
    pyproject_path = project_root / "pyproject.toml"

    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)

    return pyproject["project"]["version"]


class DocumentationGenerator:
    """Generate documentation from page module docstrings."""

    def __init__(self):
        """Initialize the documentation generator."""
        self.user_workflow_pages = USER_WORKFLOW_PAGES
        self.admin_pages = ADMIN_PAGES
        self.excluded_pages = EXCLUDED_PAGES
        log.info("Documentation generator initialized")

    def extract_docstring(self, module_name: str) -> tuple[str, str]:
        """Extract docstring from a page module by parsing the file.

        Args:
            module_name: Name of the module (e.g., 'home', 'new_job')

        Returns:
            tuple: (module_name, docstring)
        """
        # Get the file path
        pages_dir = Path(__file__).parent / "pages"
        module_file = pages_dir / f"{module_name}.py"

        # Read and parse the file to extract docstring
        with open(module_file, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())

        # Get module docstring
        docstring = ast.get_docstring(tree)

        return module_name, docstring.strip()

    def generate_introduction_section(self) -> str:
        """Generate introduction section with service overview and architecture.

        Returns:
            str: Markdown formatted introduction section
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return INTRO_TEMPLATE.format(timestamp=timestamp)

    def generate_user_workflow_section(self) -> str:
        """Generate user workflow section with sequential pages.

        Returns:
            str: Markdown formatted user workflow section
        """
        workflow = WORKFLOW_TEMPLATE

        for i, (module_name, page_title) in enumerate(self.user_workflow_pages, 1):
            _, docstring = self.extract_docstring(module_name)

            # Create section header
            workflow += f"### {i}. {page_title}\n\n"

            # Add docstring content, user-facing part only
            workflow += clean_docstring(docstring) + "\n\n"

            # Add screenshot image with max-width styling
            workflow += (
                f'<img src="/assets/docs/screenshots/{module_name}.png" '
                f'alt="{page_title}" style="max-width: 100%; height: auto;" />\n\n'
            )

            # Add specific next step name
            if i < len(self.user_workflow_pages):
                next_page_title = self.user_workflow_pages[i][1]
                workflow += f"**Next Step**: {next_page_title} →\n\n"

        workflow += "---\n\n"
        return workflow

    def generate_admin_section(self) -> str:
        """Generate administration section with admin pages.

        Returns:
            str: Markdown formatted administration section
        """
        admin = ADMIN_TEMPLATE

        for module_name, page_title in self.admin_pages:
            _, docstring = self.extract_docstring(module_name)

            # Create section header
            admin += f"### {page_title}\n\n"

            # Add docstring content, user-facing part only
            admin += clean_docstring(docstring) + "\n\n"

            # Add screenshot image with max-width styling
            admin += (
                f'<img src="/assets/docs/screenshots/{module_name}.png" '
                f'alt="{page_title}" style="max-width: 100%; height: auto;" />\n\n'
            )

        admin += "---\n\n"
        return admin

    def generate_full_documentation(self) -> str:
        """Generate complete documentation markdown.

        Returns:
            str: Complete markdown documentation
        """
        log.info("Generating documentation")

        # Generate all sections
        intro = self.generate_introduction_section()
        workflow = self.generate_user_workflow_section()
        admin = self.generate_admin_section()

        # Combine all sections with footer
        full_doc = intro + workflow + admin + FOOTER_TEMPLATE + "\n"

        log.info("Documentation generated successfully")
        return full_doc

    def write_static_documentation(self, output_file: Path) -> None:
        """Generate and write the static documentation file.

        Args:
            output_file: Path to write documentation.md

        Returns:
            None
        """
        output_file.write_text(self.generate_full_documentation(), encoding="utf-8")


def setup_logging():
    """Configure logging for CLI operations."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def generate_documentation(
    job_id_finished: str,
    job_id_new: str,
    headless: bool = True,
    markdown_only: bool = False,
) -> int:
    """Run the documentation generation workflow.

    Args:
        job_id_finished: Finished job ID to use for screenshot generation
        job_id_new: Unfinished job ID to use for screenshot generation
        headless: Run browser in headless mode (default: True)
        markdown_only: Rewrite documentation.md only, skipping screenshot capture.
            A docstring or template edit changes the markdown and nothing else, and
            that path needs no browser, no dev stack and no job IDs.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    setup_logging()

    log.info(f"Generating documentation for version {get_app_version()}")

    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    if markdown_only:
        log.info("Skipping screenshot generation (--markdown-only)")
    else:
        SCREENSHOTS_DIR.mkdir(exist_ok=True)

        log.info("Starting screenshot generation...")
        screenshot_gen = ScreenshotGenerator(
            job_id_finished, job_id_new, headless=headless
        )
        try:
            # Generate all screenshots (fails on first error)
            # Assumes dev_up.sh mock is already running
            screenshot_gen.generate_all_screenshots(SCREENSHOTS_DIR)
            log.info("All screenshots captured successfully")
        finally:
            screenshot_gen.cleanup()

    log.info("Generating static documentation files...")
    DocumentationGenerator().write_static_documentation(DOCUMENTATION_FILE)

    log.info("Documentation generated successfully!")
    log.info(f"  - Markdown: {DOCUMENTATION_FILE}")
    if not markdown_only:
        log.info(f"  - Screenshots: {SCREENSHOTS_DIR}/")

    return 0


def main():
    """Parse arguments and run documentation generation."""
    parser = argparse.ArgumentParser(
        description="Generate static documentation with screenshots"
    )
    parser.add_argument(
        "job_id_new",
        type=str,
        nargs="?",
        help="Unfinished Job ID to use for screenshot generation",
    )
    parser.add_argument(
        "job_id_finished",
        type=str,
        nargs="?",
        help="Finished Job ID to use for screenshot generation",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Show browser window during screenshot capture (for debugging)",
    )
    parser.add_argument(
        "--markdown-only",
        action="store_true",
        help="Rewrite documentation.md from the page docstrings and leave the "
        "screenshots alone (needs no job IDs and no running dev stack)",
    )

    args = parser.parse_args()

    # The job IDs only feed the screenshots, so they are required exactly when
    # screenshots are being captured.
    if not args.markdown_only and not (args.job_id_new and args.job_id_finished):
        parser.error(
            "job_id_new and job_id_finished are required unless --markdown-only is set"
        )

    sys.exit(
        generate_documentation(
            args.job_id_finished,
            args.job_id_new,
            headless=not args.no_headless,
            markdown_only=args.markdown_only,
        )
    )


if __name__ == "__main__":
    main()
