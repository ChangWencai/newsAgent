"""pytest 共享 fixtures"""
import pytest
from src.storage.database import Database


@pytest.fixture
def db():
    """每个测试函数获得独立的内存数据库"""
    database = Database(':memory:')
    yield database
    database._conn.close()
