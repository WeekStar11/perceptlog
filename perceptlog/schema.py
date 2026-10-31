# -*- coding: utf-8 -*-
"""数据结构：一条感知条目、一张对比卡片、一份日报。

这里用 dataclass + 手写校验，而不是 pydantic：整个项目对模型的输出只做“容错解析”，
不需要完整的 schema 校验能力，少一个依赖，装起来更快。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

CHANNELS = ("视觉", "听觉", "嗅觉", "味觉", "触觉", "本体觉", "设备推送")
ORIGINS = ("生物感官", "电子感官")

# 模型偶尔会写同义词，这里统一归一到固定枚举，避免整条数据被丢掉
CHANNEL_ALIASES = {
    "看": "视觉", "看见": "视觉", "眼睛": "视觉", "屏幕": "视觉", "图像": "视觉", "画面": "视觉",
    "听": "听觉", "听见": "听觉", "耳朵": "听觉", "声音": "听觉", "语音": "听觉",
    "闻": "嗅觉", "气味": "嗅觉", "鼻子": "嗅觉", "味道": "嗅觉",
    "尝": "味觉", "口感": "味觉", "舌头": "味觉", "吃": "味觉",
    "摸": "触觉", "触碰": "触觉", "皮肤": "触觉", "温度": "触觉",
    "身体": "本体觉", "体感": "本体觉", "内感受": "本体觉", "感觉": "本体觉",
    "推送": "设备推送", "通知": "设备推送", "应用": "设备推送", "弹窗": "设备推送",
}

ORIGIN_ALIASES = {
    "生物": "生物感官", "生物感官": "生物感官", "自身感官": "生物感官", "人体": "生物感官",
    "电子": "电子感官", "电子感官": "电子感官", "设备": "电子感官", "机器": "电子感官",
}


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, (list, tuple)):
        return "、".join(str(item) for item in value)
    return str(value).strip()


def _norm_channel(value: Any) -> str:
    key = _text(value)
    if key in CHANNELS:
        return key
    if key in CHANNEL_ALIASES:
        return CHANNEL_ALIASES[key]
    return "视觉"


def _norm_origin(value: Any) -> str:
    key = _text(value)
    if key in ORIGINS:
        return key
    if key in ORIGIN_ALIASES:
        return ORIGIN_ALIASES[key]
    return "生物感官"


@dataclass
class PerceptItem:
    """一条被感知到的信息。"""

    content: str
    channel: str = "视觉"
    origin: str = "生物感官"
    time: str = "未标注"
    detail: str = ""

    def __post_init__(self) -> None:
        self.channel = _norm_channel(self.channel)
        self.origin = _norm_origin(self.origin)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PerceptItem":
        content = _text(data.get("content") or data.get("text") or data.get("item"))
        if not content:
            raise ValueError("条目缺少 content 字段")
        return cls(
            content=content,
            channel=data.get("channel", "视觉"),
            origin=data.get("origin", "生物感官"),
            time=_text(data.get("time"), "未标注") or "未标注",
            detail=_text(data.get("detail")),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InsightCard:
    """对比分析中的一张卡片。"""

    title: str
    finding: str
    evidence: str = ""

    @classmethod
    def from_any(cls, value: Any) -> "InsightCard":
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            return cls(title="对比", finding=value, evidence="")
        if isinstance(value, dict):
            finding = _text(value.get("finding") or value.get("text") or value.get("content"))
            return cls(
                title=_text(value.get("title"), "对比") or "对比",
                finding=finding,
                evidence=_text(value.get("evidence")),
            )
        raise ValueError("无法识别的对比卡片：%r" % (value,))


@dataclass
class DayReport:
    """对一天的感知结构做整体判断。"""

    overview: str = ""
    comparison: List[InsightCard] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    one_sentence: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DayReport":
        cards: List[InsightCard] = []
        for item in data.get("comparison") or []:
            try:
                cards.append(InsightCard.from_any(item))
            except ValueError:
                continue
        suggestions = data.get("suggestions") or data.get("advice") or []
        if isinstance(suggestions, str):
            suggestions = [suggestions]
        return cls(
            overview=_text(data.get("overview") or data.get("summary")),
            comparison=cards,
            suggestions=[_text(item) for item in suggestions if _text(item)],
            one_sentence=_text(data.get("one_sentence") or data.get("conclusion")),
        )
