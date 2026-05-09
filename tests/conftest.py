"""pytest 共享 fixtures"""
import os
import tempfile
import pytest
from src.storage.database import Database


@pytest.fixture
def db(tmp_path):
    """每个测试函数获得隔离的临时文件数据库"""
    db_file = str(tmp_path / "test.db")
    database = Database(db_file)
    yield database
