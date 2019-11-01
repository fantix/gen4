import edgedb
import pytest
from starlette.config import environ
from starlette.testclient import TestClient

environ["TESTING"] = "TRUE"
environ["SERVER_ENABLED_MODULES"] = "submission, auth, objects"


@pytest.fixture(autouse=True, scope="session")
def setup_test_database():
    from .server import config
    from .server.app import app

    print("Connecting to root database for test database setup...")
    conn = edgedb.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=str(config.DB_PASSWORD),
        admin=config.DB_ADMIN,
        database=config.DB_DATABASE_ROOT,
        timeout=config.DB_CONNECT_TIMEOUT,
    )
    try:
        try:
            print("Attempting to create test database...")
            conn.execute(f"CREATE DATABASE {config.DB_DATABASE}")
            print("Test database created.")
        except edgedb.InternalServerError:
            print("Test database existed, reusing.")
        print("Running migration...")
        with TestClient(app) as client:
            client.get("/migrate")
        print("Migration done.")
        yield
        if not config.TEST_KEEP_DB:
            print("Dropping test database...")
            conn.execute(f"DROP DATABASE {config.DB_DATABASE}")
            print("Test database dropped.")
    finally:
        conn.close()


@pytest.fixture()
def client():
    from .server.app import app

    with TestClient(app) as client:
        yield client
