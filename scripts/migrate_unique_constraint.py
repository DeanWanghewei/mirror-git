"""
Database migration script to update unique constraints on repositories table.

Changes:
1. Remove unique constraint from 'name' column
2. Remove unique constraint from 'url' column
3. Add composite unique constraint on (url, gitea_owner)

This allows the same GitHub repository to be mirrored to different Gitea organizations.
"""

import sqlite3
from pathlib import Path


def migrate_sqlite_database(db_path: str):
    """
    Migrate SQLite database to update unique constraints.

    SQLite doesn't support dropping constraints directly, so we need to:
    1. Create a new table with the correct schema
    2. Copy data from the old table
    3. Drop the old table
    4. Rename the new table

    Args:
        db_path: Path to SQLite database file
    """
    if not Path(db_path).exists():
        print(f"Database file not found: {db_path}")
        print("No migration needed - database will be created with correct schema.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if repositories table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='repositories'
        """)

        if not cursor.fetchone():
            print("repositories table not found - no migration needed")
            return

        # Backup existing data
        print("Creating backup of repositories table...")
        cursor.execute("DROP TABLE IF EXISTS repositories_backup")
        cursor.execute("CREATE TABLE repositories_backup AS SELECT * FROM repositories")

        # Get current table info
        cursor.execute("PRAGMA table_info(repositories)")
        columns = cursor.fetchall()
        print(f"Found {len(columns)} columns in repositories table")

        # Create new table with updated schema
        print("Creating new repositories table with updated constraints...")
        cursor.execute("DROP TABLE IF EXISTS repositories_new")
        cursor.execute("""
            CREATE TABLE repositories_new (
                id INTEGER PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                owner VARCHAR(255) NOT NULL,
                url VARCHAR(512) NOT NULL,
                description TEXT,
                enabled BOOLEAN DEFAULT 1,
                tags VARCHAR(512),
                gitea_owner VARCHAR(255),
                local_path VARCHAR(512),
                sync_interval INTEGER DEFAULT 3600,
                priority INTEGER DEFAULT 0,
                size_mb REAL DEFAULT 0.0,
                last_sync_time DATETIME,
                last_sync_status VARCHAR(50) DEFAULT 'pending',
                sync_error_message TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT uix_url_gitea_owner UNIQUE (url, gitea_owner)
            )
        """)

        # Drop old indexes if they exist (from the old table)
        # Note: SQLite will automatically drop indexes when the table is dropped

        # Create indexes on new table
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_repositories_name ON repositories_new (name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_repositories_url ON repositories_new (url)")

        # Copy data from old table to new table
        print("Copying data to new table...")
        cursor.execute("""
            INSERT INTO repositories_new
            SELECT * FROM repositories
        """)

        rows_copied = cursor.rowcount
        print(f"Copied {rows_copied} rows")

        # Drop old table and rename new table
        print("Replacing old table with new table...")
        cursor.execute("DROP TABLE repositories")
        cursor.execute("ALTER TABLE repositories_new RENAME TO repositories")

        # Commit changes
        conn.commit()
        print("✓ Migration completed successfully!")
        print(f"✓ Removed unique constraints from 'name' and 'url' columns")
        print(f"✓ Added composite unique constraint on (url, gitea_owner)")
        print(f"✓ You can now mirror the same GitHub repo to different Gitea organizations")

    except sqlite3.IntegrityError as e:
        print(f"\n✗ Migration failed due to data conflict: {e}")
        print("\nThis might happen if you already have duplicate URLs in your database.")
        print("You need to manually resolve the conflicts:")
        print("1. Check repositories_backup table for conflicting entries")
        print("2. Set different gitea_owner values for duplicate URLs")
        print("3. Re-run this migration script")
        conn.rollback()

    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        print("Rolling back changes...")
        conn.rollback()

    finally:
        conn.close()


def main():
    """Main migration function."""
    import sys

    # Default database path
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
        # Handle sqlite:/// prefix
        if db_path.startswith("sqlite:///"):
            db_path = db_path.replace("sqlite:///", "")
    else:
        db_path = "./data/sync.db"

    print(f"Migrating database: {db_path}")
    print("-" * 60)

    migrate_sqlite_database(db_path)

    print("-" * 60)
    print("\nNext steps:")
    print("1. Restart your application")
    print("2. You can now add the same GitHub repository with different gitea_owner values")


if __name__ == "__main__":
    main()
