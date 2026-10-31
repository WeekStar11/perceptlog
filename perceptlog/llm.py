# -*- coding: utf-8 -*-
"""模型工厂：在线与离线模型共用 ChatOpenAI（OpenAI 兼容协议），换一个 base_url 即可切换。"""
from __future__ import annotations

from typing import Any

from langchain_openai import ChatOpenAI

from .config import PROVIDER_PRESETS, MissingCredential, Settings


def build_llm(settings: Settings, streaming: bool = True) -> ChatOpenAI:
    """按配置创建对话模型。"""
    if settings.is_demo:
        raise MissingCredential("演示模式不创建真实模型，请改用 demo 流程。")
    if not settings.api_key:
        env_name = PROVIDER_PRESETS[settings.provider]["api_key_env"]
        raise MissingCredential(
            "没有找到 %s。请在 .env 里填写，或在界面左侧输入。" % env_name
        )

    kwargs: dict[str, Any] = {
        "model": settings.model,
        "temperature": settings.temperature,
        "api_key": settings.api_key,
        "streaming": streaming,
        "timeout": 90,
        "max_retries": 2,
    }
    if settings.base_url:
        kwargs["base_url"] = settings.base_url
    return ChatOpenAI(**kwargs)
