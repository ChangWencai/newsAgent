"""DFA 敏感词检测模块

使用 DFA（确定性有限自动机）算法实现高效多模式匹配，
支持通过文件 mtime 检测实现热重载。
"""

import logging
import os

logger = logging.getLogger(__name__)

_DEFAULT_WORD_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data",
    "sensitive_words.txt",
)


class SensitiveWordFilter:
    """基于 DFA 树的敏感词过滤器"""

    def __init__(self, word_file: str | None = None):
        self._word_file = word_file or _DEFAULT_WORD_FILE
        self._dfa: dict = {}
        self._last_mtime: float = 0.0
        self._load_words()

    def _load_words(self) -> None:
        """加载或热重载敏感词文件（仅在 mtime 变化时重建 DFA 树）"""
        if not os.path.exists(self._word_file):
            logger.warning("敏感词文件不存在: %s", self._word_file)
            return

        current_mtime = os.path.getmtime(self._word_file)
        if current_mtime == self._last_mtime:
            return

        self._dfa = {}
        with open(self._word_file, encoding="utf-8") as f:
            for line in f:
                word = line.strip()
                if word:
                    self._add_word(word)

        self._last_mtime = current_mtime
        logger.info("已加载敏感词库: %s", self._word_file)

    def _add_word(self, word: str) -> None:
        """将一个敏感词插入 DFA 树"""
        node = self._dfa
        for char in word:
            node = node.setdefault(char, {})
        node["_end"] = True

    def check(self, text: str | None) -> list[str]:
        """检测文本中包含的敏感词

        Args:
            text: 待检测文本

        Returns:
            命中的敏感词列表（去重）
        """
        if not text:
            return []

        self._load_words()

        hits: list[str] = []
        text_len = len(text)

        for i in range(text_len):
            node = self._dfa
            for j in range(i, text_len):
                char = text[j]
                if char not in node:
                    break
                node = node[char]
                if node.get("_end"):
                    hits.append(text[i : j + 1])

        return list(dict.fromkeys(hits))


# 模块级单例
_filter: SensitiveWordFilter | None = None


def check_sensitive_words(text: str | None) -> list[str]:
    """便捷函数：使用全局单例检测敏感词"""
    global _filter
    if _filter is None:
        _filter = SensitiveWordFilter()
    return _filter.check(text)
