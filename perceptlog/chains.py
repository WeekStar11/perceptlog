# -*- coding: utf-8 -*-
"""LangChain 链：抽取 → 分析 → 追问，全部用 LCEL 组合，没有隐藏的魔法。"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Sequence, Tuple

from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable, RunnableLambda

from .config import Settings
from .demo import run_demo
from .llm import build_llm
from .parsing import parse_items, parse_report
from .prompts import (ANALYZE_HUMAN, ANALYZE_SYSTEM, CHAT_SYSTEM, EXTRACT_HUMAN,
                      EXTRACT_SYSTEM)
from .report import build_stats
from .schema import DayReport, PerceptItem

MAX_LOG_CHARS = 12000


def _clip(text: str) -> str:
    """超长日志截断，并在结尾留下可读的提示，避免直接把上下文撑爆。"""
    text = (text or "").strip()
    if len(text) <= MAX_LOG_CHARS:
        return text
    return text[:MAX_LOG_CHARS] + "\n\n（日志过长，后面部分已截断）"


def build_extract_chain(llm: Runnable) -> Runnable:
    """日志文本 → List[PerceptItem]。

    system 提示里带着 JSON 示例，花括号很多，所以用 SystemMessage 直接塞进去，
    不走模板渲染——否则示例里的 {"time": ...} 会被当成模板变量。
    """
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=EXTRACT_SYSTEM),
        ("human", EXTRACT_HUMAN),
    ])
    return prompt | llm | StrOutputParser() | RunnableLambda(parse_items)


def build_analyze_chain(llm: Runnable) -> Runnable:
    """条目 + 统计 → DayReport。"""
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=ANALYZE_SYSTEM),
        ("human", ANALYZE_HUMAN),
    ])
    return prompt | llm | StrOutputParser() | RunnableLambda(parse_report)


def build_payload(items: Sequence[PerceptItem]) -> str:
    """把条目与统计拼成分析链的输入。"""
    payload: Dict[str, Any] = {
        "stats": build_stats(items),
        "items": [item.to_dict() for item in items],
    }
    return json.dumps(payload, ensure_ascii=False)


def build_chat_chain(llm: Runnable, items: Sequence[PerceptItem]) -> Runnable:
    """带日志上下文的追问链：历史消息 + 当天的条目与统计。"""
    digest = json.dumps([item.to_dict() for item in items], ensure_ascii=False, indent=1)
    stats = build_stats(items)
    stats_text = (
        "共 %d 条，生物感官 %d 条，电子感官 %d 条，最高频通道是%s。"
        % (stats["total"], stats["bio"], stats["elec"], stats["top_channel"])
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", CHAT_SYSTEM),
        MessagesPlaceholder("history"),
        ("human", "{question}"),
    ]).partial(digest=digest, stats=stats_text)
    return prompt | llm | StrOutputParser()


def analyze_day(day_text: str, settings: Settings) -> Tuple[List[PerceptItem], DayReport]:
    """完整流程：演示模式走规则，真实模式走两条 LCEL 链。"""
    if settings.is_demo:
        return run_demo(day_text)

    llm = build_llm(settings)
    items = build_extract_chain(llm).invoke({"log": _clip(day_text)})
    report = build_analyze_chain(llm).invoke({"payload": build_payload(items)})
    return items, report

