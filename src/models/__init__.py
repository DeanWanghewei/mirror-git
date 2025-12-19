"""
Database models for GitHub Mirror Sync using SQLAlchemy.

Defines data models for repositories, sync history, and application configuration.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

Base = declarative_base()


class Repository(Base):
    """Repository model for storing GitHub repository information."""

    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    owner = Column(String(255), nullable=False)
    url = Column(String(512), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True)
    tags = Column(String(512), nullable=True)  # Comma-separated tags

    # Gitea target configuration
    gitea_owner = Column(String(255), nullable=True)  # Organization or user namespace in Gitea

    # Local path
    local_path = Column(String(512), nullable=True)

    # Sync settings
    sync_interval = Column(Integer, default=3600)  # Seconds
    priority = Column(Integer, default=0)  # 0=normal, -1=low, 1=high

    # Statistics
    size_mb = Column(Float, default=0.0)
    last_sync_time = Column(DateTime, nullable=True)
    last_sync_status = Column(String(50), default="pending")  # pending, syncing, success, failed
    sync_error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "owner": self.owner,
            "url": self.url,
            "description": self.description,
            "enabled": self.enabled,
            "tags": self.tags.split(",") if self.tags else [],
            "local_path": self.local_path,
            "gitea_owner": self.gitea_owner,
            "sync_interval": self.sync_interval,
            "priority": self.priority,
            "size_mb": self.size_mb,
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "last_sync_status": self.last_sync_status,
            "sync_error_message": self.sync_error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class SyncHistory(Base):
    """SyncHistory model for tracking synchronization records."""

    __tablename__ = "sync_history"

    id = Column(Integer, primary_key=True)
    repository_id = Column(Integer, nullable=False, index=True)
    repository_name = Column(String(255), nullable=False)

    # Operation details
    operation_type = Column(String(50), nullable=False)  # clone, update, push
    status = Column(String(50), nullable=False)  # success, failed, partial
    error_message = Column(Text, nullable=True)

    # Statistics
    start_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, default=0.0)
    files_added = Column(Integer, default=0)
    files_modified = Column(Integer, default=0)
    files_deleted = Column(Integer, default=0)
    data_size_mb = Column(Float, default=0.0)

    # Additional info
    log_output = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "repository_id": self.repository_id,
            "repository_name": self.repository_name,
            "operation_type": self.operation_type,
            "status": self.status,
            "error_message": self.error_message,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "files_added": self.files_added,
            "files_modified": self.files_modified,
            "files_deleted": self.files_deleted,
            "data_size_mb": self.data_size_mb,
            "log_output": self.log_output,
            "created_at": self.created_at.isoformat(),
        }


class AppConfig(Base):
    """AppConfig model for storing application configuration."""

    __tablename__ = "app_config"

    id = Column(Integer, primary_key=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    description = Column(String(512), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "key": self.key,
            "value": self.value,
            "description": self.description,
            "updated_at": self.updated_at.isoformat(),
        }


class SyncLog(Base):
    """SyncLog model for storing detailed sync logs."""

    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True)
    sync_history_id = Column(Integer, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    level = Column(String(10), nullable=False)  # DEBUG, INFO, WARNING, ERROR
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "sync_history_id": self.sync_history_id,
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
        }


class Database:
    """Database manager for SQLAlchemy operations."""

    def __init__(self, database_url: str = "sqlite:///mirror_sync.db"):
        """Initialize database connection.

        Args:
            database_url: Database connection URL (default: SQLite file)
        """
        self.database_url = database_url

        # Create engine with appropriate connection pooling
        if database_url.startswith("sqlite:///:memory:"):
            # In-memory database for testing
            self.engine = create_engine(
                database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool
            )
        else:
            self.engine = create_engine(database_url, echo=False)

        self.SessionLocal = sessionmaker(bind=self.engine)

    def init_db(self) -> None:
        """Create all tables in the database."""
        Base.metadata.create_all(self.engine)

    def drop_db(self) -> None:
        """Drop all tables from the database (for testing)."""
        Base.metadata.drop_all(self.engine)

    def get_session(self):
        """Get a new database session.

        Returns:
            SQLAlchemy session object
        """
        return self.SessionLocal()


# Global database instance
_db_instance: Optional[Database] = None


def init_database(database_url: str = "sqlite:///mirror_sync.db") -> Database:
    """Initialize global database instance.

    Args:
        database_url: Database connection URL

    Returns:
        Database instance
    """
    global _db_instance
    _db_instance = Database(database_url)
    _db_instance.init_db()
    return _db_instance


def get_database() -> Database:
    """Get global database instance.

    Returns:
        Database instance

    Raises:
        RuntimeError: If database not initialized
    """
    global _db_instance
    if _db_instance is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _db_instance
