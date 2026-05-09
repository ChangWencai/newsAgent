"""pytest 共享 fixtures"""
import pytest
from src.storage.database import Database


@pytest.fixture
def db():
    """每个测试函数获得独立的内存数据库"""
    database = Database(':memory:')
    yield database
    database._conn.close()


@pytest.fixture
def app(db):
    from main import create_app

    app = create_app(db=db)
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()
