"""Output the final text to system clipboard."""

import pyperclip


def send(text: str) -> None:
    """Copy text to clipboard."""
    if not text:
        return
    try:
        pyperclip.copy(text)
        print(f"[Clipboard] 已复制（{len(text)} 字符）")
    except Exception as e:
        print(f"[Output Error] {e}")
