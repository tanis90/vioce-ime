"""voice-ime: 极简语音输入法

Usage:
    1. 配置 .env（参考 .env.example）
    2. pip install -r requirements.txt
    3. python main.py
    4. 按住 F9 录音，松开后自动识别并输出
    5. 若结果不满意，修改后按 F10 可快速更新词表（交互式）
"""

import asyncio
import os
import sys
import time
from typing import Optional

import keyboard

from config import Config
from recorder import record_audio
from asr_provider import ASRProviderFactory
from glossary import Glossary
from llm_postprocess import postprocess
from output import send


class VoiceIME:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.glossary = Glossary(cfg)
        self._send = send
        self.asr_provider = ASRProviderFactory.create(cfg.asr_provider, cfg)
        self._last_raw: Optional[str] = None
        self._last_final: Optional[str] = None

    # ---------- core loop ----------

    async def run(self) -> None:
        print("=" * 50)
        print("voice-ime  极简语音输入法")
        print("=" * 50)
        print(f"热键: 按住 [{self.cfg.hotkey_record}] 录音 | [{self.cfg.hotkey_feedback}] 反馈纠正")
        print(f"输出模式: {self.cfg.output_mode}")
        print(f"词表文件: {self.cfg.glossary_path}（当前 {len(self.glossary.items())} 条）")
        print("=" * 50)

        while True:
            await asyncio.sleep(0.05)

            if keyboard.is_pressed(self.cfg.hotkey_record):
                await self._handle_record()
                await asyncio.sleep(0.3)  # debounce

            if keyboard.is_pressed(self.cfg.hotkey_feedback):
                await self._handle_feedback()
                await asyncio.sleep(0.3)  # debounce

    async def _handle_record(self) -> None:
        """Record -> ASR -> Glossary correct -> LLM postprocess -> Output."""
        import time
        t0 = time.time()

        # 1. Record
        audio_path = await asyncio.to_thread(record_audio, self.cfg)
        if not audio_path or os.path.getsize(audio_path) < 1024:
            print("[Warn] 录音过短，已忽略")
            return

        # 2. ASR
        asr_result = await asyncio.to_thread(self.asr_provider.transcribe, audio_path)
        raw_text = asr_result.get("text", "")
        if not raw_text:
            print("[Warn] 识别失败，无结果")
            return
        self._last_raw = raw_text
        print(f"[ASR] {asr_result.get('provider', '?')} | 延迟: {asr_result.get('latency', '-')}s | 结果: {raw_text}")

        # 3. Glossary string-level correction
        corrected = self.glossary.correct(raw_text)
        if corrected != raw_text:
            print(f"[词表替换] {raw_text} -> {corrected}")

        # 4. LLM post-processing
        final_text = await asyncio.to_thread(postprocess, corrected, self.cfg, self.glossary)
        self._last_final = final_text

        # 5. Output
        total = time.time() - t0
        print(f"\n[Done] 最终结果: {final_text}")
        print(f"[Done] 全流程耗时: {total:.2f}s\n")
        self._send(final_text)

    async def _handle_feedback(self) -> None:
        """Interactive feedback to update glossary."""
        if not self._last_raw or not self._last_final:
            print("[反馈] 尚无识别记录，请先录音识别一次")
            return

        print("\n--- 反馈纠正 ---")
        print(f"识别原文: {self._last_raw}")
        print(f"上次输出: {self._last_final}")
        print("选项: [1] 把「上次输出」整体加入词表  [2] 手动输入正确文本并建立映射  [3] 查看当前词表  [Enter] 取消")
        try:
            choice = await asyncio.to_thread(input, "请选择: ")
        except EOFError:
            return

        choice = choice.strip()
        if choice == "1":
            self.glossary.add(self._last_raw, self._last_final)
        elif choice == "2":
            try:
                wrong = await asyncio.to_thread(input, "请输入语音识别错误的内容: ")
                correct = await asyncio.to_thread(input, "请输入正确内容: ")
                self.glossary.add(wrong.strip(), correct.strip())
            except EOFError:
                pass
        elif choice == "3":
            items = self.glossary.items()
            if not items:
                print("[词表] 当前为空")
            else:
                for k, v in list(items.items())[:20]:
                    print(f"  {k} -> {v}")
                if len(items) > 20:
                    print(f"  ... 共 {len(items)} 条")
        else:
            print("[反馈] 已取消")
        print("---")


def main() -> None:
    cfg = Config.from_env()
    ime = VoiceIME(cfg)
    try:
        asyncio.run(ime.run())
    except KeyboardInterrupt:
        print("\n[System] 已退出")


if __name__ == "__main__":
    main()
