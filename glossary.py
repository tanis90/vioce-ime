"""Professional glossary: collect hotwords for ASR enhancement.

职责变更:
    旧: ASR 结果出来后做字符串前向最大匹配替换（纯字符串层面）
    新: 作为热词收集器，通过 F10 反馈沉淀术语，供 ASR 调用时注入 hotwords

词表格式（保持不变）:
    {"错误读音": "正确术语", ...}
    - Key 是历史识别错误的写法（便于追溯）
    - Value 是需要 ASR 加强识别的标准术语
    - ASR 调用时提取所有 values 去重后作为 hotwords 注入
"""

import json
import os
from typing import Dict, Optional

from config import Config


class Glossary:
    """热词收集器：通过 F10 反馈沉淀术语，供 ASR 调用时注入 hotwords。"""

    def __init__(self, cfg: Config):
        self.path = cfg.glossary_path
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
        """Add or update a (wrong, correct) pair."""
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

    # ---------- hotwords for ASR ----------

    def hotwords(self) -> list[str]:
        """Extract all unique correct terms for ASR hotwords injection."""
        if not self._table:
            return []
        # Deduplicate while preserving order
        seen = set()
        result = []
        for v in self._table.values():
            if v not in seen:
                seen.add(v)
                result.append(v)
        return result

    def hotwords_prompt(self) -> str:
        """Build a readable summary of current hotwords for display."""
        words = self.hotwords()
        if not words:
            return "当前无热词"
        return f"当前热词 ({len(words)} 个): {', '.join(words[:10])}" + (
            " ..." if len(words) > 10 else ""
        )
