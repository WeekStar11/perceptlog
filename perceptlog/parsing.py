# -*- coding: utf-8 -*-
"""把模型返回的文本解析成结构化结果。

大模型（尤其是小参数本地模型）经常在 JSON 外面套一层解释文字或 Markdown 代码块，
这里做三件事：剥围栏、找第一个完整的 JSON 片段、按模型容错校验。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from .schema import DayReport, PerceptItem


class ParseError(ValueError):
    """模型输出无法解析成 JSON 时抛出。"""


_FENCE_RE = re.compile(r"```(?:json|JSON)?\s*(.+?)```", re.S)


def strip_code_fence(text: str) -> str:
    """去掉 ```json ... ``` 围栏；没有围栏就返回原文。"""
    match = _FENCE_RE.search(text or "")
    if match:
        return match.group(1).strip()
    return (text or "").strip()


def find_json_candidate(text: str) -> str:
    """从任意文本中截出第一个括号配平的 JSON 片段（数组或对象）。"""
    text = strip_code_fence(text)
    starts = [i for i in (text.find("["), text.find("{")) if i != -1]
    if not starts:
        raise ParseError("模型输出里没有找到 JSON 片段")
    start = min(starts)
    opener = text[start]
    closer = "]" if opener == "[" else "}"
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    # 没有配平（输出被截断），把剩下的都交给 json 去报错
    return text[start:]


def loads_json(text: str) -> Any:
    """容错地把文本解析成 Python 对象。"""
    candidate = find_json_candidate(text)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:  # 常见：尾逗号、单引号
        repaired = re.sub(r",\s*([\]}])", r"\1", candidate)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            raise ParseError("JSON 解析失败：%s" % exc) from exc


def parse_items(raw: str) -> List[PerceptItem]:
    """解析条目数组；兼容 {"items": [...]} 这种包了一层的写法。"""
    data = loads_json(raw)
    if isinstance(data, dict):
        for key in ("items", "entries", "data", "list"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
        else:
            raise ParseError("没有在对象里找到条目数组")

    if not isinstance(data, list) or not data:
        raise ParseError("条目数组为空")

    items: List[PerceptItem] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        try:
            items.append(PerceptItem.from_dict(entry))
        except ValueError:
            continue

    if not items:
        raise ParseError("条目全部校验失败")
    return items


def parse_report(raw: str) -> DayReport:
    """解析对比分析结果。"""
    data = loads_json(raw)
    if isinstance(data, list) and data and isinstance(data[0], dict):
        data = data[0]
    if not isinstance(data, dict):
        raise ParseError("分析结果不是 JSON 对象")

    return DayReport.from_dict(data)
