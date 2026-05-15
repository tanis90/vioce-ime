"""Configuration management for voice-ime."""

import os
from dataclasses import dataclass, field
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
    volcengine_poll_interval: float = 0.1   # 轮询间隔（秒）

    # --- 阿里 Qwen-Omni ---
    dashscope_api_key: Optional[str] = None
    ali_asr_model: str = "qwen-omni-turbo"   # 或 qwen-omni-turbo-0119

    # --- 火山引擎 TOS（字节 Seed-ASR 上传音频需要） ---
    tos_access_key: Optional[str] = None
    tos_secret_key: Optional[str] = None
    tos_endpoint: str = "tos-cn-shanghai.volces.com"
    tos_bucket: Optional[str] = None

    # --- LLM (OpenAI-compatible) ---
    llm_api_key: Optional[str] = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 2048
    llm_timeout: float = 30.0

    # --- Audio ---
    audio_chunk: int = 1024
    audio_format: int = 0x0008                # pyaudio.paInt16 (set in runtime)
    audio_channels: int = 1
    audio_rate: int = 16000
    audio_temp_file: str = "temp_recording.wav"

    # --- Hotkeys ---
    hotkey_record: str = "f9"                 # 按住录音，松开发送
    hotkey_feedback: str = "f10"              # 反馈当前结果以更新词表

    # --- Glossary ---
    glossary_path: str = "glossary.json"
    glossary_max_match_len: int = 20          # 最大前向匹配长度（字符）

    # --- Output ---
    # 仅支持剪贴板，保持极简
    output_mode: str = "clipboard"

    @classmethod
    def from_env(cls) -> "Config":
        """Build config from environment variables with sensible defaults."""
        return cls(
            asr_provider=os.getenv("ASR_PROVIDER", "zhipu"),
            # 智谱
            zhipu_api_key=os.getenv("ZHIPU_API_KEY"),
            # 字节
            volcengine_api_key=os.getenv("VOLCENGINE_API_KEY"),
            volcengine_poll_interval=float(os.getenv("VOLCENGINE_POLL_INTERVAL", "0.1")),
            # 阿里
            dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
            ali_asr_model=os.getenv("ALI_ASR_MODEL", "qwen-omni-turbo"),
            # TOS
            tos_access_key=os.getenv("TOS_ACCESS_KEY"),
            tos_secret_key=os.getenv("TOS_SECRET_KEY"),
            tos_endpoint=os.getenv("TOS_ENDPOINT", "tos-cn-shanghai.volces.com"),
            tos_bucket=os.getenv("TOS_BUCKET"),
            # LLM
            llm_api_key=os.getenv("LLM_API_KEY"),
            llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
            llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.0")),
            llm_max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2048")),
            llm_timeout=float(os.getenv("LLM_TIMEOUT", "30.0")),
            audio_temp_file=os.getenv("AUDIO_TEMP_FILE", "temp_recording.wav"),
            hotkey_record=os.getenv("HOTKEY_RECORD", "f9"),
            hotkey_feedback=os.getenv("HOTKEY_FEEDBACK", "f10"),
            glossary_path=os.getenv("GLOSSARY_PATH", "glossary.json"),
        )
