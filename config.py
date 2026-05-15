"""Configuration management for voice-ime."""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load .env if present
load_dotenv()


@dataclass
class Config:
    # --- ASR Provider ---
    # 可选: "zhipu" (默认) | "volcengine" | "ali"
    asr_provider: str = "zhipu"

    # --- 智谱 GLM-ASR ---
    zhipu_api_key: Optional[str] = None

    # --- 字节 Seed-ASR ---
    volcengine_api_key: Optional[str] = None
    volcengine_poll_interval: float = 0.1

    # --- 阿里 Qwen-Omni ---
    dashscope_api_key: Optional[str] = None
    ali_asr_model: str = "qwen-omni-turbo"

    # --- 火山引擎 TOS（字节 Seed-ASR 上传音频需要） ---
    tos_access_key: Optional[str] = None
    tos_secret_key: Optional[str] = None
    tos_endpoint: str = "tos-cn-shanghai.volces.com"
    tos_bucket: Optional[str] = None

    # --- Audio ---
    audio_chunk: int = 1024
    audio_format: int = 0x0008                # pyaudio.paInt16 (set in runtime)
    audio_channels: int = 1
    audio_rate: int = 16000
    audio_temp_file: str = "temp_recording.wav"

    # --- Hotkeys ---
    hotkey_record: str = "f9"
    hotkey_feedback: str = "f10"

    # --- Glossary ---
    glossary_path: str = "glossary.json"
    glossary_max_match_len: int = 20

    # --- Output ---
    output_mode: str = "clipboard"

    @classmethod
    def from_env(cls) -> "Config":
        """Build config from environment variables with sensible defaults."""
        return cls(
            asr_provider=os.getenv("ASR_PROVIDER", "zhipu"),
            zhipu_api_key=os.getenv("ZHIPU_API_KEY"),
            volcengine_api_key=os.getenv("VOLCENGINE_API_KEY"),
            volcengine_poll_interval=float(os.getenv("VOLCENGINE_POLL_INTERVAL", "0.1")),
            dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
            ali_asr_model=os.getenv("ALI_ASR_MODEL", "qwen-omni-turbo"),
            tos_access_key=os.getenv("TOS_ACCESS_KEY"),
            tos_secret_key=os.getenv("TOS_SECRET_KEY"),
            tos_endpoint=os.getenv("TOS_ENDPOINT", "tos-cn-shanghai.volces.com"),
            tos_bucket=os.getenv("TOS_BUCKET"),
            audio_temp_file=os.getenv("AUDIO_TEMP_FILE", "temp_recording.wav"),
            hotkey_record=os.getenv("HOTKEY_RECORD", "f9"),
            hotkey_feedback=os.getenv("HOTKEY_FEEDBACK", "f10"),
            glossary_path=os.getenv("GLOSSARY_PATH", "glossary.json"),
        )
