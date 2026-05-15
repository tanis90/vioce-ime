"""Professional glossary for ASR error correction.

词表机制:
    - 持久化存储在 JSON 文件里，格式 {"错误读音": "正确术语", ...}
    - 在 ASR 结果出来后先做一轮前向最大匹配替换（纯字符串层面）
    - 替换后的文本再送给 LLM，Prompt 里也会注入词表供 LLM 参考
    - 用户可以通过反馈热键把 "LLM 修正前 → 用户最终修改后" 的映射自动/半自动加入词表
"""

import json
import os
from typing import Dict, Optional, Tuple

from config import Config


class Glossary:
    """A simple in-memory glossary backed by a JSON file."""

    def __init__(self, cfg: Config):
        self.path = cfg.glossary_path
        self.max_len = cfg.glossary_max_match_len
        self._table: Dict[str, str] = {}
        self.load()

    # ---------- persistence ----------

    def load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self._table = json.load(f)
                print(f"[词表] 已加载 {len(self._table)} 条术语")
            except Exception as e:
                print(f"[词表 Warning] 加载失败: {e}")
                self._table = {}
        else:
            self._table = {}

    def save(self) -> None:
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._table, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[词表 Error] 保存失败: {e}")

    # ---------- CRUD ----------

    def add(self, wrong: str, correct: str) -> None:
        """Add or update a correction pair."""
        wrong = wrong.strip()
        correct = correct.strip()
        if wrong and correct:
            self._table[wrong] = correct
            self.save()
            print(f"[词表] 已添加: '{wrong}' → '{correct}'")

    def remove(self, wrong: str) -> bool:
        if wrong in self._table:
            del self._table[wrong]
            self.save()
            return True
        return False

    def get(self, wrong: str) -> Optional[str]:
        return self._table.get(wrong)

    def items(self) -> Dict[str, str]:
        return dict(self._table)

    # ---------- correction ----------

    def correct(self, text: str) -> str:
        """Apply forward-maximum matching correction on the text.

        This is a pure string-level patch *before* LLM processing.
        It's fast and deterministic.
        """
        if not self._table:
            return text

        corrected = []
        i = 0
        n = len(text)
        keys = list(self._table.keys())
        # Sort keys by length descending so longer matches are tried first
        keys.sort(key=lambda k: len(k), reverse=True)

        while i < n:
            matched = False
            max_try = min(self.max_len, n - i)
            for key in keys:
                if len(key) <= max_try and text[i : i + len(key)] == key:
                    corrected.append(self._table[key])
                    i += len(key)
                    matched = True
                    break
            if not matched:
                corrected.append(text[i])
                i += 1

        return "".join(corrected)

    # ---------- diff-based learning ----------

    def suggest_pairs(self, before: str, after: str) -> list[Tuple[str, str]]:
        """Heuristically extract changed substrings between before/after.

        Returns a list of candidate (wrong, correct) tuples.
        Current implementation is naive: if overall strings differ,
        it returns the whole text as a candidate. User decides whether to add.
        """
        if before == after:
            return []
        # Naive whole-text suggestion; can be replaced with LCS diff later
        return [(before, after)]


def build_glossary_prompt(table: Dict[str, str]) -> str:
    """Build a prompt snippet that injects glossary into LLM context."""
    if not table:
        return ""
    lines = ["以下是一份专业术语对照表，请在润色和纠错时严格参考："]
    for k, v in table.items():
        lines.append(f"  - 语音中若出现「{k}」，应纠正为「{v}」")
    return "\n".join(lines)
