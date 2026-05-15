"""LLM post-processing: polish ASR output with glossary-aware prompt."""

from typing import Optional

import openai

import os

from config import Config
from glossary import Glossary, build_glossary_prompt


def _load_system_prompt() -> str:
    """Load system prompt from external markdown file."""
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "llm_postprocess.md")
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    # Fallback to default prompt if file is missing
    return (
        "你是一台语音输入法的后处理引擎。用户的输入来自语音识别（ASR），可能存在以下问题：\n"
        "1. 同音字、谐音字错误\n"
        "2. 缺少标点或标点错误\n"
        "3. 语气词、重复词过多\n"
        "4. 专有名词、术语识别错误\n\n"
        "你的任务：\n"
        "- 根据提供的专业术语对照表进行纠正\n"
        "- 补充合适的标点符号，让文本更通顺\n"
        "- 删除无意义的重复和语气词冗余\n"
        "- 保持用户原意，不要扩写或改变语义\n"
        "- 直接输出最终文本，不要加任何解释、前缀或后缀\n"
    )


def postprocess(raw_text: str, cfg: Config, glossary: Glossary) -> str:
    """Send raw ASR text to LLM for polishing.

    Args:
        raw_text: The text coming out of ASR (already glossary-corrected at string level).
        cfg: App config containing LLM credentials.
        glossary: Glossary instance to inject into prompt.

    Returns:
        Polished text. On failure, returns the raw_text unchanged.
    """
    if not cfg.llm_api_key:
        print("[LLM Warning] 未配置 LLM_API_KEY，跳过 LLM 后处理")
        return raw_text

    client = openai.OpenAI(
        api_key=cfg.llm_api_key,
        base_url=cfg.llm_base_url,
        timeout=cfg.llm_timeout,
    )

    glossary_snippet = build_glossary_prompt(glossary.items())
    user_content = raw_text
    if glossary_snippet:
        user_content = f"{glossary_snippet}\n\n请处理以下文本：\n{raw_text}"
    else:
        user_content = f"请处理以下文本：\n{raw_text}"

    import time
    t0 = time.time()
    print("[LLM] 请求后处理…")
    try:
        kwargs = {"model": cfg.llm_model, "max_tokens": cfg.llm_max_tokens}
        # 只有配置了非 None 温度才传入，且做好不支持时的降级
        if cfg.llm_temperature is not None:
            kwargs["temperature"] = cfg.llm_temperature

        resp = client.chat.completions.create(
            messages=[
                {"role": "system", "content": _load_system_prompt()},
                {"role": "user", "content": user_content},
            ],
            **kwargs,
        )
        result = resp.choices[0].message.content.strip()
        print(f"[LLM] 后处理结果 ({time.time()-t0:.2f}s): {result}")
        return result
    except Exception as e:
        err_msg = str(e).lower()
        # 常见的不支持 temperature 的错误特征
        if "temperature" in err_msg or "unsupported parameter" in err_msg:
            print(f"[LLM Warning] 厂家不支持 temperature，已降级重试")
            try:
                resp = client.chat.completions.create(
                    model=cfg.llm_model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                    max_tokens=cfg.llm_max_tokens,
                )
                result = resp.choices[0].message.content.strip()
                print(f"[LLM] 后处理结果: {result}")
                return result
            except Exception as e2:
                print(f"[LLM Error] 降级后仍失败: {e2}")
                return raw_text
        print(f"[LLM Error] {e}")
        return raw_text
