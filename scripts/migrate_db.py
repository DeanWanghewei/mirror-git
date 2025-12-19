"""
Database migration script to add gitea_owner column to repositories table.

This script safely adds the gitea_owner column to existing databases.
Run this before starting the application if you have existing data.
"""

import sqlite3
from pathlib import Path
from sqlalchemy import inspect


def migrate_sqlite_database(db_url: str):
    """
    Migrate SQLite database to add gitea_owner column.

    Args:
        db_url: Database URL (e.g., "sqlite:///path/to/db.db")
    """
    # Extract file path from SQLite URL
    if not db_url.startswith("sqlite:///"):
        print(f"Unsupported database URL: {db_url}")
        return

    db_path = db_url.replace("sqlite:///", "")

    if not Path(db_path).exists():
        print(f"Database file not found: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if gitea_owner column already exists
        cursor.execute("PRAGMA table_info(repositories)")
        columns = [col[1] for col in cursor.fetchall()]

        if "gitea_owner" in columns:
            print("✓ gitea_owner column already exists")
            return

        # Add gitea_owner column
        print("Adding gitea_owner column to repositories table...")
        cursor.execute("""
            ALTER TABLE repositories
            ADD COLUMN gitea_owner VARCHAR(255) NULLABLE DEFAULT NULL
        """)

        conn.commit()
        print("✓ Migration completed successfully!")

    except Exception as e:
        print(f"✗ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()


def migrate_other_databases(engine):
    """
    Migrate other database backends (PostgreSQL, MySQL) using SQLAlchemy.

    Args:
        engine: SQLAlchemy engine instance
    """
    from sqlalchemy import text, Column, String
    from src.models import Repository, Base

    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('repositories')]

    if "gitea_owner" in columns:
        print("✓ gitea_owner column already exists")
        return

    print("Adding gitea_owner column to repositories table...")

    with engine.connect() as conn:
        if engine.dialect.name == "postgresql":
            conn.execute(text(
                "ALTER TABLE repositories ADD COLUMN gitea_owner VARCHAR(255) DEFAULT NULL"
            ))
        elif engine.dialect.name == "mysql":
            conn.execute(text(
                "ALTER TABLE repositories ADD COLUMN gitea_owner VARCHAR(255) DEFAULT NULL"
            ))
        conn.commit()

    print("✓ Migration completed successfully!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        db_url = sys.argv[1]
    else:
        db_url = "sqlite:///./data/sync.db"

    if db_url.startswith("sqlite://"):
        migrate_sqlite_database(db_url)
    else:
        from sqlalchemy import create_engine
        engine = create_engine(db_url)
        migrate_other_databases(engine)
