"""
Tests for database models and database manager.
"""

import pytest
from datetime import datetime
from sqlalchemy import inspect
from src.models import (
    Repository, SyncHistory, AppConfig, SyncLog, Database,
    init_database, get_database, Base, _db_instance
)


@pytest.fixture
def test_db():
    """Create an in-memory test database."""
    db = Database("sqlite:///:memory:")
    db.init_db()
    yield db
    db.drop_db()


@pytest.fixture(autouse=True)
def reset_global_db():
    """Reset global database instance between tests."""
    import src.models
    src.models._db_instance = None
    yield
    src.models._db_instance = None


def test_database_in_memory_creation():
    """Test creating an in-memory database."""
    db = Database("sqlite:///:memory:")
    assert db.database_url == "sqlite:///:memory:"
    assert db.engine is not None
    assert db.SessionLocal is not None


def test_database_file_creation(tmp_path):
    """Test creating a file-based database."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    db = Database(db_url)
    assert db.database_url == db_url
    assert db.engine is not None


def test_database_init_db(test_db):
    """Test database table initialization."""
    test_db.init_db()

    # Check that tables are created
    inspector = inspect(test_db.engine)
    tables = inspector.get_table_names()

    assert "repositories" in tables
    assert "sync_history" in tables
    assert "app_config" in tables
    assert "sync_logs" in tables


def test_database_get_session(test_db):
    """Test getting a database session."""
    session = test_db.get_session()
    assert session is not None
    session.close()


def test_database_drop_db(test_db):
    """Test dropping database tables."""
    test_db.drop_db()

    inspector = inspect(test_db.engine)
    tables = inspector.get_table_names()

    assert len(tables) == 0


def test_init_database_global():
    """Test initializing global database instance."""
    db = init_database("sqlite:///:memory:")
    assert db is not None
    assert get_database() is db


def test_get_database_without_init():
    """Test getting database without initialization."""
    with pytest.raises(RuntimeError, match="Database not initialized"):
        get_database()


def test_repository_creation(test_db):
    """Test creating a repository record."""
    session = test_db.get_session()

    repo = Repository(
        name="test-repo",
        owner="test-owner",
        url="https://github.com/test-owner/test-repo.git"
    )

    session.add(repo)
    session.commit()
    session.refresh(repo)

    assert repo.id is not None
    assert repo.name == "test-repo"
    assert repo.owner == "test-owner"
    assert repo.enabled is True
    assert repo.sync_interval == 3600
    assert repo.priority == 0

    session.close()


def test_repository_defaults(test_db):
    """Test repository default values."""
    session = test_db.get_session()

    repo = Repository(
        name="test-repo",
        owner="test-owner",
        url="https://github.com/test-owner/test-repo.git"
    )

    session.add(repo)
    session.commit()

    assert repo.enabled is True
    assert repo.sync_interval == 3600
    assert repo.priority == 0
    assert repo.size_mb == 0.0
    assert repo.last_sync_status == "pending"
    assert repo.created_at is not None
    assert repo.updated_at is not None

    session.close()


def test_repository_to_dict(test_db):
    """Test repository to_dict method."""
    session = test_db.get_session()

    repo = Repository(
        name="test-repo",
        owner="test-owner",
        url="https://github.com/test-owner/test-repo.git",
        description="A test repository",
        tags="python,testing",
        size_mb=100.5,
        last_sync_status="success"
    )

    session.add(repo)
    session.commit()
    session.refresh(repo)

    repo_dict = repo.to_dict()

    assert repo_dict["name"] == "test-repo"
    assert repo_dict["owner"] == "test-owner"
    assert repo_dict["url"] == "https://github.com/test-owner/test-repo.git"
    assert repo_dict["description"] == "A test repository"
    assert repo_dict["tags"] == ["python", "testing"]
    assert repo_dict["size_mb"] == 100.5
    assert repo_dict["last_sync_status"] == "success"

    session.close()


def test_repository_to_dict_no_tags(test_db):
    """Test repository to_dict with no tags."""
    session = test_db.get_session()

    repo = Repository(
        name="test-repo",
        owner="test-owner",
        url="https://github.com/test-owner/test-repo.git"
    )

    session.add(repo)
    session.commit()

    repo_dict = repo.to_dict()
    assert repo_dict["tags"] == []

    session.close()


def test_repository_unique_name(test_db):
    """Test repository name uniqueness."""
    session = test_db.get_session()

    repo1 = Repository(
        name="test-repo",
        owner="owner1",
        url="https://github.com/owner1/test-repo.git"
    )
    repo2 = Repository(
        name="test-repo",
        owner="owner2",
        url="https://github.com/owner2/test-repo.git"
    )

    session.add(repo1)
    session.commit()

    session.add(repo2)
    with pytest.raises(Exception):  # SQLAlchemy will raise IntegrityError
        session.commit()

    session.close()


def test_sync_history_creation(test_db):
    """Test creating a sync history record."""
    session = test_db.get_session()

    history = SyncHistory(
        repository_id=1,
        repository_name="test-repo",
        operation_type="clone",
        status="success",
        duration_seconds=10.5
    )

    session.add(history)
    session.commit()
    session.refresh(history)

    assert history.id is not None
    assert history.repository_id == 1
    assert history.repository_name == "test-repo"
    assert history.operation_type == "clone"
    assert history.status == "success"

    session.close()


def test_sync_history_to_dict(test_db):
    """Test sync history to_dict method."""
    session = test_db.get_session()

    now = datetime.utcnow()
    history = SyncHistory(
        repository_id=1,
        repository_name="test-repo",
        operation_type="update",
        status="success",
        start_time=now,
        end_time=now,
        duration_seconds=5.0,
        files_added=10,
        files_modified=5,
        files_deleted=2,
        data_size_mb=50.0
    )

    session.add(history)
    session.commit()

    history_dict = history.to_dict()

    assert history_dict["repository_id"] == 1
    assert history_dict["repository_name"] == "test-repo"
    assert history_dict["operation_type"] == "update"
    assert history_dict["status"] == "success"
    assert history_dict["duration_seconds"] == 5.0
    assert history_dict["files_added"] == 10
    assert history_dict["files_modified"] == 5
    assert history_dict["files_deleted"] == 2
    assert history_dict["data_size_mb"] == 50.0

    session.close()


def test_sync_history_to_dict_no_end_time(test_db):
    """Test sync history to_dict with no end_time."""
    session = test_db.get_session()

    history = SyncHistory(
        repository_id=1,
        repository_name="test-repo",
        operation_type="clone",
        status="success"
    )

    session.add(history)
    session.commit()

    history_dict = history.to_dict()
    assert history_dict["end_time"] is None

    session.close()


def test_app_config_creation(test_db):
    """Test creating app config records."""
    session = test_db.get_session()

    config = AppConfig(
        key="github_token",
        value="token_value_123",
        description="GitHub API token"
    )

    session.add(config)
    session.commit()
    session.refresh(config)

    assert config.id is not None
    assert config.key == "github_token"
    assert config.value == "token_value_123"
    assert config.description == "GitHub API token"

    session.close()


def test_app_config_to_dict(test_db):
    """Test app config to_dict method."""
    session = test_db.get_session()

    config = AppConfig(
        key="sync_interval",
        value="3600",
        description="Default sync interval in seconds"
    )

    session.add(config)
    session.commit()

    config_dict = config.to_dict()

    assert config_dict["key"] == "sync_interval"
    assert config_dict["value"] == "3600"
    assert config_dict["description"] == "Default sync interval in seconds"

    session.close()


def test_app_config_unique_key(test_db):
    """Test app config key uniqueness."""
    session = test_db.get_session()

    config1 = AppConfig(key="setting1", value="value1")
    config2 = AppConfig(key="setting1", value="value2")

    session.add(config1)
    session.commit()

    session.add(config2)
    with pytest.raises(Exception):  # SQLAlchemy will raise IntegrityError
        session.commit()

    session.close()


def test_sync_log_creation(test_db):
    """Test creating sync log records."""
    session = test_db.get_session()

    log = SyncLog(
        sync_history_id=1,
        level="INFO",
        message="Sync operation started"
    )

    session.add(log)
    session.commit()
    session.refresh(log)

    assert log.id is not None
    assert log.sync_history_id == 1
    assert log.level == "INFO"
    assert log.message == "Sync operation started"
    assert log.timestamp is not None

    session.close()


def test_sync_log_to_dict(test_db):
    """Test sync log to_dict method."""
    session = test_db.get_session()

    log = SyncLog(
        sync_history_id=1,
        level="ERROR",
        message="An error occurred during sync"
    )

    session.add(log)
    session.commit()

    log_dict = log.to_dict()

    assert log_dict["sync_history_id"] == 1
    assert log_dict["level"] == "ERROR"
    assert log_dict["message"] == "An error occurred during sync"
    assert log_dict["timestamp"] is not None

    session.close()


def test_sync_log_levels(test_db):
    """Test creating logs with different levels."""
    session = test_db.get_session()

    levels = ["DEBUG", "INFO", "WARNING", "ERROR"]

    for level in levels:
        log = SyncLog(
            sync_history_id=1,
            level=level,
            message=f"Test {level} message"
        )
        session.add(log)

    session.commit()

    logs = session.query(SyncLog).all()
    assert len(logs) == 4

    for i, level in enumerate(levels):
        assert logs[i].level == level

    session.close()


def test_database_session_isolation(test_db):
    """Test database session isolation."""
    session1 = test_db.get_session()
    session2 = test_db.get_session()

    repo1 = Repository(
        name="test-repo-1",
        owner="owner1",
        url="https://github.com/owner1/test-repo-1.git"
    )

    session1.add(repo1)
    session1.commit()

    # Session 2 should be able to see the committed data
    repos = session2.query(Repository).all()
    assert len(repos) == 1

    session1.close()
    session2.close()


def test_repository_timestamp_update(test_db):
    """Test repository timestamp updates."""
    session = test_db.get_session()

    repo = Repository(
        name="test-repo",
        owner="owner",
        url="https://github.com/owner/test-repo.git"
    )

    session.add(repo)
    session.commit()

    created_at = repo.created_at
    updated_at = repo.updated_at

    # Update repository
    repo.enabled = False
    session.commit()

    # created_at should not change
    assert repo.created_at == created_at
    # updated_at should be updated
    assert repo.updated_at >= updated_at

    session.close()


def test_multiple_repositories(test_db):
    """Test managing multiple repositories."""
    session = test_db.get_session()

    repos = [
        Repository(
            name=f"repo-{i}",
            owner=f"owner-{i}",
            url=f"https://github.com/owner-{i}/repo-{i}.git"
        )
        for i in range(5)
    ]

    session.add_all(repos)
    session.commit()

    all_repos = session.query(Repository).all()
    assert len(all_repos) == 5

    session.close()


def test_sync_history_query(test_db):
    """Test querying sync history."""
    session = test_db.get_session()

    for i in range(3):
        history = SyncHistory(
            repository_id=1,
            repository_name="test-repo",
            operation_type="update",
            status="success" if i < 2 else "failed"
        )
        session.add(history)

    session.commit()

    success_count = session.query(SyncHistory).filter(
        SyncHistory.status == "success"
    ).count()
    assert success_count == 2

    failed_count = session.query(SyncHistory).filter(
        SyncHistory.status == "failed"
    ).count()
    assert failed_count == 1

    session.close()


def test_database_with_postgresql_url():
    """Test database initialization with PostgreSQL URL."""
    db = Database("postgresql://user:password@localhost/dbname")
    assert db.database_url == "postgresql://user:password@localhost/dbname"
    assert db.engine is not None


def test_database_with_mysql_url():
    """Test database initialization with MySQL URL."""
    db = Database("mysql+pymysql://user:password@localhost/dbname")
    assert db.database_url == "mysql+pymysql://user:password@localhost/dbname"
    assert db.engine is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
