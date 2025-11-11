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
        raise AssertionError("docker/init.sql is not up-to-date.")
