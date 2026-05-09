"""敏感词过滤模块测试"""

import os
import tempfile

import pytest

from src.validator.sensitive import SensitiveWordFilter, check_sensitive_words


@pytest.fixture
def word_file():
    """创建临时敏感词文件"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        f.write("赌博\n色情\n暴力\n反动\n违禁品\n")
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def filter_instance(word_file):
    return SensitiveWordFilter(word_file=word_file)


class TestSensitiveWordFilter:
    def test_dfa_basic_match(self, filter_instance):
        """含敏感词文本返回命中列表"""
        hits = filter_instance.check("这篇文章包含赌博内容")
        assert "赌博" in hits
        assert len(hits) >= 1

    def test_dfa_no_match(self, filter_instance):
        """无敏感词文本返回空列表"""
        hits = filter_instance.check("这是一篇正常的科技新闻")
        assert hits == []

    def test_dfa_empty_text(self, filter_instance):
        """空文本返回空列表"""
        assert filter_instance.check("") == []
        assert filter_instance.check(None) == []

    def test_dfa_multiple_matches(self, filter_instance):
        """多个敏感词全部命中"""
        hits = filter_instance.check("赌博和色情和暴力内容")
        assert "赌博" in hits
        assert "色情" in hits
        assert "暴力" in hits
        assert len(hits) == 3

    def test_dfa_hot_reload(self, word_file):
        """修改词库文件后自动检测新词"""
        f = SensitiveWordFilter(word_file=word_file)
        # 初始词库没有"黑客"
        assert f.check("黑客攻击") == []

        # 追加新词
        with open(word_file, "a", encoding="utf-8") as fh:
            fh.write("黑客\n")

        # 应当热重载检测到新词
        hits = f.check("黑客攻击系统")
        assert "黑客" in hits


class TestModuleFunction:
    def test_check_sensitive_words_returns_list(self):
        """模块级便捷函数返回列表"""
        result = check_sensitive_words("测试")
        assert isinstance(result, list)
