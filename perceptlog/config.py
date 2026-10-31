# -*- coding: utf-8 -*-
"""运行配置：在线模型（DeepSeek / OpenAI）与离线模型（Ollama）统一走 OpenAI 兼容接口。"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

try:  # python-dotenv 是可选的：没有它也能用系统环境变量跑起来
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

# 三种真实模型 + 一种无需联网的本地演示模式
PROVIDER_PRESETS = {
    "deepseek": {
        "label": "DeepSeek（在线）",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "api_key_env": "DEEPSEEK_API_KEY",
        "api_key_default": "",
        "note": "国内可直接访问，性价比高，推荐默认使用。",
    },
    "openai": {
        "label": "OpenAI（在线）",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "api_key_env": "OPENAI_API_KEY",
        "api_key_default": "",
        "note": "需要可访问 OpenAI 的网络环境。",
    },
    "ollama": {
        "label": "Ollama（离线）",
        "base_url": "http://localhost:11434/v1",
        "model": "qwen2.5:7b",
        "api_key_env": "OLLAMA_API_KEY",
        "api_key_default": "ollama",
        "note": "本机运行 ollama serve 并 ollama pull qwen2.5:7b 后即可完全离线使用。",
    },
    "demo": {
        "label": "本地演示模式（不调用大模型）",
        "base_url": "",
        "model": "rule-based",
        "api_key_env": "PERCEPTLOG_DEMO",
        "api_key_default": "demo",
        "note": "用关键词规则跑通完整流程，仅用于界面预览与断网演示。",
    },
}

DEFAULT_PROVIDER = os.getenv("PERCEPTLOG_PROVIDER", "deepseek").strip().lower()


class MissingCredential(RuntimeError):
    """没有配置 API Key 时抛出，界面上要给出可读的提示。"""


@dataclass(frozen=True)
class Settings:
    """一次运行所需的全部模型参数。"""

    provider: str = DEFAULT_PROVIDER
    model: str = ""
    base_url: Optional[str] = None
    api_key: str = ""
    temperature: float = 0.3

    @classmethod
    def from_env(cls) -> "Settings":
        provider = DEFAULT_PROVIDER if DEFAULT_PROVIDER in PROVIDER_PRESETS else "deepseek"
        preset = PROVIDER_PRESETS[provider]
        return cls(
            provider=provider,
            model=os.getenv("PERCEPTLOG_MODEL", preset["model"]),
            base_url=os.getenv("PERCEPTLOG_BASE_URL", preset["base_url"]) or None,
            api_key=os.getenv(preset["api_key_env"], preset["api_key_default"]),
            temperature=float(os.getenv("PERCEPTLOG_TEMPERATURE", "0.3")),
        )

    @property
    def is_demo(self) -> bool:
        return self.provider == "demo"

    @property
    def is_ready(self) -> bool:
        return self.is_demo or bool(self.api_key)

    def with_overrides(self, **kwargs) -> "Settings":
        data = {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "api_key": self.api_key,
            "temperature": self.temperature,
        }
        data.update({k: v for k, v in kwargs.items() if v is not None})
        return Settings(**data)
