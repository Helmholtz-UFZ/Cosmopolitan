"""
Test to verify that init.sql is up-to-date with managed_init.sql and Kombu DDL.

This test ensures that:
1. docker/init.sql exists
2. docker/managed_init.sql exists
3. init.sql can be regenerated from managed_init.sql + Kombu DDL
4. The regenerated init.sql matches the current one

If this test fails, run: python cosmopolitan_app/build_init_sql.py
"""

import subprocess
from pathlib import Path


def test_init_sql_is_up_to_date():
    """Test that init.sql is up-to-date with managed_init.sql and Kombu DDL."""
    # Determine paths
    repo_root = Path(__file__).parent.parent
    init_sql_path = repo_root / "docker" / "init.sql"
    build_script = repo_root / "cosmopolitan_app" / "build_init_sql.py"

    # Verify files exist
    assert init_sql_path.exists(), "docker/init.sql does not exist"
    assert build_script.exists(), "cosmopolitan_app/build_init_sql.py does not exist"

    # Read current init.sql
    current_init_sql = init_sql_path.read_text()

    # Create temporary directory for regenerated init.sql

    # Run build script to regenerate init.sql
    result = subprocess.run(
        ["python3", str(build_script)],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    # Check that build script succeeded
    if result.returncode != 0:
        error_msg = (
            f"Failed to regenerate init.sql:\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )
        raise AssertionError(error_msg)

    # Read regenerated init.sql
    regenerated_init_sql = init_sql_path.read_text()

    # Compare current and regenerated
    if current_init_sql != regenerated_init_sql:
        # Save regenerated version for debugging
        debug_file = repo_root / "docker" / "init.sql.regenerated"
        debug_file.write_text(regenerated_init_sql)

        error_msg = (
            "\n\n"
            "=" * 80 + "\n"
            "ERROR: init.sql is OUT OF DATE!\n"
            "=" * 80 + "\n"
            "\n"
            "The current docker/init.sql does not match what would be generated\n"
            "from managed_init.sql and Kombu's SQLAlchemy models.\n"
            "\n"
            "This usually means:\n"
            "  1. You edited docker/init.sql directly (instead of managed_init.sql)\n"  # noqa
            "  2. The Kombu version changed and the broker schema is outdated\n"
            "  3. You forgot to regenerate init.sql after editing managed_init.sql\n"  # noqa
            "\n"
            "To fix this:\n"
            "  1. Run: python cosmopolitan_app/build_init_sql.py\n"
            "  2. Review the changes in docker/init.sql\n"
            "  3. Commit the updated init.sql\n"
            "\n"
            f"A regenerated version has been saved to: {debug_file}\n"
            "You can compare them with: diff docker/init.sql docker/init.sql.regenerated\n"  # noqa
            "\n"
            "=" * 80 + "\n"
        )
        raise AssertionError(error_msg)


def test_managed_init_sql_exists():
    """Test that managed_init.sql exists."""
    repo_root = Path(__file__).parent.parent
    managed_init_sql = repo_root / "docker" / "managed_init.sql"

    assert managed_init_sql.exists(), (
        "docker/managed_init.sql does not exist. "
        "This file should contain all manually managed database tables."
    )

    # Verify it has content
    content = managed_init_sql.read_text()
    assert len(content) > 100, "managed_init.sql appears to be empty or too small"

    # Verify it doesn't contain Kombu tables (should be auto-generated)
    assert "kombu_queue" not in content, (
        "managed_init.sql should not contain Kombu tables. "
        "Remove them - they are auto-generated from Kombu's models."
    )
    assert "kombu_message" not in content, (
        "managed_init.sql should not contain Kombu tables. "
        "Remove them - they are auto-generated from Kombu's models."
    )


def test_build_script_is_executable():
    """Test that build_init_sql.py can be executed."""
    repo_root = Path(__file__).parent.parent
    build_script = repo_root / "cosmopolitan_app" / "build_init_sql.py"

    assert build_script.exists(), "build_init_sql.py does not exist"

    # Try to run it with --help or similar (without actually building)
    # Just verify it's importable
    result = subprocess.run(
        ["python3", "-m", "py_compile", str(build_script)],
        capture_output=True,
    )

    assert (
        result.returncode == 0
    ), f"build_init_sql.py has syntax errors:\n{result.stderr.decode()}"
