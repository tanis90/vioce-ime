"""
统一 ASR Provider 层
====================
支持三家端到端 ASR：智谱（默认）、字节、阿里。
用法:
    from asr_provider import ASRProviderFactory
    from config import Config

    cfg = Config.from_env()
    provider = ASRProviderFactory.create(cfg.asr_provider, cfg)
    result = provider.transcribe("temp_recording.wav")
    print(result["text"])

返回统一格式:
    {
        "text": "识别文本",
        "usage": {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int},
        "provider": "zhipu" | "volcengine" | "ali",
        "latency": float,   # 秒
        "raw": dict,        # 原始响应
    }
"""

import base64
import json
import os
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Optional

import requests

# 复用 TOS 上传（字节需要）
try:
    from upload_to_tos import upload_file as tos_upload_file
except ImportError:
    tos_upload_file = None


class BaseASRProvider(ABC):
    """ASR Provider 抽象基类。"""

    name: str = "base"

    @abstractmethod
    def transcribe(self, audio_path: str, **kwargs: Any) -> dict:
        """
        识别本地音频文件。

        Args:
            audio_path: 本地音频文件路径
            **kwargs:   各 provider 可能支持的额外参数
                        - prompt / system_prompt: 人设/上下文注入
                        - hotwords: 热词列表
        Returns:
            统一格式的结果 dict
        """
        raise NotImplementedError


class ZhipuASRProvider(BaseASRProvider):
    """
    智谱 GLM-ASR-2512
    - 接口: OpenAI 兼容 HTTP (multipart)
    - 延迟: ~0.7s
    - 价格: ¥0.06/分钟
    """

    name = "zhipu"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://open.bigmodel.cn/api/paas/v4/audio/transcriptions"

    def transcribe(self, audio_path: str, **kwargs: Any) -> dict:
        t0 = time.perf_counter()
        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = {"model": "glm-asr-2512", "stream": "false"}

        prompt = kwargs.get("prompt") or kwargs.get("system_prompt")
        hotwords = kwargs.get("hotwords")
        if prompt:
            data["prompt"] = prompt
        if hotwords:
            data["hotwords"] = hotwords

        with open(audio_path, "rb") as f:
            files = {"file": (os.path.basename(audio_path), f)}
            resp = requests.post(self.url, headers=headers, data=data, files=files, timeout=60)
        resp.raise_for_status()
        raw = resp.json()
        t1 = time.perf_counter()

        text = raw.get("text", "")
        if not text and "choices" in raw:
            text = raw["choices"][0]["message"]["content"]

        return {
            "text": text,
            "usage": raw.get("usage", {}),
            "provider": self.name,
            "latency": round(t1 - t0, 2),
            "raw": raw,
        }


class VolcengineASRProvider(BaseASRProvider):
    """
    字节 Seed-ASR 2.0
    - 接口: HTTP 异步（提交 → 轮询）
    - 延迟: ~1.3s（轮询间隔 0.1s）
    - 价格: ¥0.013/分钟
    - 依赖: 需先上传音频到公网 URL（自动使用 TOS）
    """

    name = "volcengine"

    def __init__(
        self,
        api_key: str,
        tos_ak: Optional[str] = None,
        tos_sk: Optional[str] = None,
        tos_endpoint: str = "tos-cn-shanghai.volces.com",
        tos_bucket: Optional[str] = None,
        poll_interval: float = 0.1,
    ):
        self.api_key = api_key
        self.tos_ak = tos_ak
        self.tos_sk = tos_sk
        self.tos_endpoint = tos_endpoint
        self.tos_bucket = tos_bucket
        self.poll_interval = poll_interval
        self.submit_url = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/submit"
        self.query_url = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/query"

    def _get_headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "X-Api-Key": self.api_key,
            "X-Api-Resource-Id": "volc.seedasr.auc",
        }

    def _upload_if_needed(self, audio_path: str) -> str:
        """本地文件上传到 TOS 获取公网 URL。"""
        if tos_upload_file is None:
            raise RuntimeError("upload_to_tos 模块未找到")
        # 临时覆盖环境变量供 upload_to_tos 使用
        os.environ.setdefault("TOS_ACCESS_KEY", self.tos_ak or "")
        os.environ.setdefault("TOS_SECRET_KEY", self.tos_sk or "")
        os.environ.setdefault("TOS_ENDPOINT", self.tos_endpoint)
        os.environ.setdefault("TOS_BUCKET", self.tos_bucket or "")
        return tos_upload_file(audio_path)

    def transcribe(self, audio_path: str, **kwargs: Any) -> dict:
        t0 = time.perf_counter()

        # 1. 上传
        audio_url = self._upload_if_needed(audio_path)
        suffix = os.path.splitext(audio_path)[1].lower().lstrip(".")

        # 2. 提交
        task_id = str(uuid.uuid4())
        headers = {
            **self._get_headers(),
            "X-Api-Request-Id": task_id,
            "X-Api-Sequence": "-1",
        }
        payload = {
            "audio": {"url": audio_url, "format": suffix},
            "request": {
                "model_name": "bigmodel",
                "enable_itn": True,
                "enable_punc": True,
                "enable_ddc": False,
            },
        }

        # prompt / hotwords → corpus.context
        prompt = kwargs.get("prompt") or kwargs.get("system_prompt")
        hotwords = kwargs.get("hotwords")
        ctx: dict = {}
        if prompt:
            ctx["context_type"] = "dialog_ctx"
            ctx["context_data"] = [{"text": prompt}]
        if hotwords:
            ctx["hotwords"] = [{"word": w} for w in hotwords]
        if ctx:
            payload["request"]["corpus"] = {"context": json.dumps(ctx, ensure_ascii=False)}

        resp = requests.post(self.submit_url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()

        # 3. 轮询
        query_headers = {**self._get_headers(), "X-Api-Request-Id": task_id}
        for _ in range(600):  # 最多 60s
            time.sleep(self.poll_interval)
            qresp = requests.post(self.query_url, headers=query_headers, json={}, timeout=30)
            data = qresp.json()
            if "result" in data and data["result"]:
                break
            status = qresp.headers.get("X-Api-Status-Code")
            if status not in ("20000001", "20000002"):
                raise RuntimeError(f"查询异常: {status} - {qresp.headers.get('X-Api-Message')}")
        else:
            raise RuntimeError("轮询超时")

        t1 = time.perf_counter()
        result = data.get("result", {})
        return {
            "text": result.get("text", ""),
            "usage": {},  # 字节不返回 token 消耗
            "provider": self.name,
            "latency": round(t1 - t0, 2),
            "raw": data,
        }


class AliASRProvider(BaseASRProvider):
    """
    阿里 Qwen-Omni-Turbo
    - 接口: OpenAI 兼容 SSE 流式
    - 延迟: ~1.0s
    - 价格: 音频输入 ¥0.025/千 token
    - 注意: 是多模态对话模型，system_prompt 易导致幻觉，建议留空
    """

    name = "ali"

    def __init__(self, api_key: str, model: str = "qwen-omni-turbo"):
        self.api_key = api_key
        self.model = model
        self.url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

    def transcribe(self, audio_path: str, **kwargs: Any) -> dict:
        t0 = time.perf_counter()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        with open(audio_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode()

        system_prompt = kwargs.get("system_prompt") or kwargs.get("prompt")
        user_prompt = kwargs.get("user_prompt", "请直接转写这段音频的原始内容，不要添加、修改或解释任何内容。")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "input_audio",
                    "input_audio": {
                        "data": f"data:;base64,{audio_b64}",
                        "format": "mp3",
                    },
                },
                {"type": "text", "text": user_prompt},
            ],
        })

        payload = {
            "model": self.model,
            "messages": messages,
            "modalities": ["text"],
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        resp = requests.post(self.url, headers=headers, json=payload, stream=True, timeout=120)
        resp.raise_for_status()

        full_text = ""
        usage = {}
        for line in resp.iter_lines():
            if not line:
                continue
            line = line.decode("utf-8")
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    if chunk.get("choices"):
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta:
                            full_text += delta["content"]
                    if chunk.get("usage"):
                        usage = chunk["usage"]
                except json.JSONDecodeError:
                    continue

        t1 = time.perf_counter()
        return {
            "text": full_text,
            "usage": usage,
            "provider": self.name,
            "latency": round(t1 - t0, 2),
            "raw": {},
        }


class ASRProviderFactory:
    """根据配置创建对应的 ASR Provider。"""

    _registry = {
        "zhipu": ZhipuASRProvider,
        "volcengine": VolcengineASRProvider,
        "ali": AliASRProvider,
    }

    @classmethod
    def create(cls, provider_name: str, cfg: Any) -> BaseASRProvider:
        """
        根据 provider_name 和配置对象创建 Provider。

        Args:
            provider_name: "zhipu" | "volcengine" | "ali"
            cfg: Config 对象（或任何包含所需属性的对象）
        """
        name = provider_name.lower().strip()
        if name not in cls._registry:
            raise ValueError(
                f"不支持的 ASR 提供商: {provider_name}\n"
                f"支持的选项: {list(cls._registry.keys())}"
            )

        if name == "zhipu":
            return ZhipuASRProvider(api_key=cfg.zhipu_api_key)

        if name == "volcengine":
            return VolcengineASRProvider(
                api_key=cfg.volcengine_api_key,
                tos_ak=cfg.tos_access_key,
                tos_sk=cfg.tos_secret_key,
                tos_endpoint=cfg.tos_endpoint,
                tos_bucket=cfg.tos_bucket,
                poll_interval=cfg.volcengine_poll_interval,
            )

        if name == "ali":
            return AliASRProvider(
                api_key=cfg.dashscope_api_key,
                model=getattr(cfg, "ali_asr_model", "qwen-omni-turbo"),
            )

        raise RuntimeError("Factory 逻辑异常")

    @classmethod
    def available_providers(cls) -> list[str]:
        return list(cls._registry.keys())
