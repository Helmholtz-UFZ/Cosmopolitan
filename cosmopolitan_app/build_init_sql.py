#!/usr/bin/env python3
"""
Build init.sql from managed_init.sql and auto-generated Kombu DDL.

This script extracts the exact PostgreSQL DDL from Kombu's SQLAlchemy models
and concatenates it with the manually managed database schema.

Usage:
    python cosmopolitan_app/build_init_sql.py
"""

import sys
from pathlib import Path

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Sequence,
    SmallInteger,
    String,
    Table,
    Text,
    create_mock_engine,
)
from sqlalchemy.dialects import postgresql


def extract_kombu_ddl() -> str:
    """Extract PostgreSQL DDL statements from Kombu's SQLAlchemy models.

    Returns:
        str: Complete DDL for Kombu broker tables (sequences, tables, indexes)
    """
    # Manually recreate Kombu's table definitions based on the source code
    # Reference: https://github.com/celery/kombu/blob/main/kombu/transport/sqlalchemy/models.py  # noqa

    metadata = MetaData()

    # Queue table - automatically registers with metadata
    Table(
        "kombu_queue",
        metadata,
        Column(
            "id",
            Integer,
            Sequence("queue_id_sequence"),
            primary_key=True,
            autoincrement=True,
        ),
        Column("name", String(200), unique=True),
        mysql_engine="InnoDB",
        sqlite_autoincrement=True,
    )

    # Message table - automatically registers with metadata
    Table(
        "kombu_message",
        metadata,
        Column(
            "id",
            Integer,
            Sequence("message_id_sequence"),
            primary_key=True,
            autoincrement=True,
        ),
        Column("visible", Boolean, default=True, index=True),
        Column("timestamp", DateTime, nullable=True, index=True),
        Column("payload", Text, nullable=False),
        Column("version", SmallInteger, nullable=False, default=1),
        Column(
            "queue_id",
            Integer,
            ForeignKey("kombu_queue.id", name="FK_kombu_message_queue"),
        ),
        Index("ix_kombu_message_timestamp_id", "timestamp", "id"),
        mysql_engine="InnoDB",
        sqlite_autoincrement=True,
    )

    # Collect all DDL statements
    ddl_statements = []

    def dump(sql, *multiparams, **params):
        compiled = sql.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
        ddl_statements.append(str(compiled))

    # Create mock engine with PostgreSQL dialect
    engine = create_mock_engine("postgresql+psycopg2://", dump)

    # Generate all DDL (sequences, tables, indexes, constraints)
    metadata.create_all(engine, checkfirst=False)

    # Post-process DDL statements to fix PostgreSQL-specific issues
    # Group statements by type for deterministic ordering
    sequences = []
    tables = []
    indexes = []
    other = []

    for statement in ddl_statements:
        statement = statement.strip()
        if not statement:
            continue

        # Group by statement type
        if statement.startswith("CREATE SEQUENCE"):
            seq_name = statement.split()[2]
            sequences.append((seq_name, statement))

        elif statement.startswith("CREATE TABLE"):
            table_name = statement.split()[2]

            # Add DEFAULT nextval() for id columns that use sequences
            # kombu_queue.id uses queue_id_sequence
            # kombu_message.id uses message_id_sequence
            if table_name == "kombu_queue":
                statement = statement.replace(
                    "id INTEGER NOT NULL,",
                    "id INTEGER NOT NULL DEFAULT nextval('queue_id_sequence'),",
                )
            elif table_name == "kombu_message":
                statement = statement.replace(
                    "id INTEGER NOT NULL,",
                    "id INTEGER NOT NULL DEFAULT nextval('message_id_sequence'),",
                )

            tables.append((table_name, statement))

        elif statement.startswith("CREATE INDEX"):
            # Extract index name for sorting
            index_name = statement.split()[2]
            indexes.append((index_name, statement))

        else:
            other.append(statement)

    # Sort each group for deterministic output
    # Respect dependency order for tables: kombu_queue before kombu_message
    sequences.sort(key=lambda x: x[0])
    indexes.sort(key=lambda x: x[0])

    # Manual ordering for tables to respect foreign key dependencies
    table_order = ["kombu_queue", "kombu_message"]
    tables_dict = dict(tables)
    tables_ordered = [
        (name, tables_dict[name]) for name in table_order if name in tables_dict
    ]

    # Sequences should match table order for clarity
    sequence_order = ["queue_id_sequence", "message_id_sequence"]
    sequences_dict = dict(sequences)
    sequences_ordered = [
        (name, sequences_dict[name])
        for name in sequence_order
        if name in sequences_dict
    ]

    # Build processed statements in order: sequences, tables, indexes, other
    processed_statements = []

    for seq_name, statement in sequences_ordered:
        processed_statements.append(f"DROP SEQUENCE IF EXISTS {seq_name} CASCADE;")
        processed_statements.append(statement + ";")

    for table_name, statement in tables_ordered:
        processed_statements.append(f"DROP TABLE IF EXISTS {table_name} CASCADE;")
        processed_statements.append(statement + ";")

    for index_name, statement in indexes:
        processed_statements.append(statement + ";")

    for statement in other:
        processed_statements.append(statement + ";")

    # Format DDL statements
    ddl_lines = [
        "-- Celery broker tables (Kombu SQLAlchemy transport)",
        "-- AUTO-GENERATED from kombu.transport.sqlalchemy.models",
        "-- DO NOT EDIT - Regenerate with: python cosmopolitan_app/build_init_sql.py",
        "",
    ]

    for statement in processed_statements:
        ddl_lines.append(statement)
        ddl_lines.append("")

    return "\n".join(ddl_lines)


def build_init_sql(file_path: str = None):
    """Build init.sql from managed_init.sql and Kombu DDL."""
    # Determine file paths
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    docker_dir = repo_root / "docker"

    managed_init_path = docker_dir / "managed_init.sql"
    if file_path:
        init_sql_path = Path(file_path)
    else:
        init_sql_path = docker_dir / "init.sql"

    # Read managed SQL
    if not managed_init_path.exists():
        raise FileNotFoundError(
            f"managed_init.sql not found at {managed_init_path}. "
            "Please create it from init.sql first."
        )

    managed_sql = managed_init_path.read_text()

    # Extract Kombu DDL
    print("Extracting Kombu DDL from SQLAlchemy models...")
    kombu_ddl = extract_kombu_ddl()

    # Build complete init.sql
    header = [
        "-- init.sql",
        "-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY",
        "--",
        "-- This file is generated by: python cosmopolitan_app/build_init_sql.py",
        "-- To make changes:",
        "--   1. Edit docker/managed_init.sql for application tables",
        "--   2. Run: python cosmopolitan_app/build_init_sql.py",
        "--   3. Test changes: pytest test/test_init_sql.py",
        "",
    ]

    complete_sql = "\n".join(header) + "\n" + managed_sql.strip() + "\n\n" + kombu_ddl

    # Write init.sql
    init_sql_path.write_text(complete_sql)


if __name__ == "__main__":
    build_init_sql(sys.argv[1] if len(sys.argv) > 1 else None)
