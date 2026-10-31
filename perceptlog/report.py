# -*- coding: utf-8 -*-
"""统计与导出：不依赖大模型，纯函数，便于测试。"""
from __future__ import annotations

from collections import Counter
from typing import Dict, List, Sequence

from .schema import DayReport, PerceptItem


def build_stats(items: Sequence[PerceptItem]) -> Dict[str, object]:
    """统计条目总数、两种来源的占比、各通道分布。"""
    total = len(items)
    origins = Counter(item.origin for item in items)
    channels = Counter(item.channel for item in items)
    bio = origins.get("生物感官", 0)
    elec = origins.get("电子感官", 0)
    top_channel = channels.most_common(1)[0][0] if channels else "—"
    return {
        "total": total,
        "bio": bio,
        "elec": elec,
        "bio_ratio": round(bio / total, 3) if total else 0.0,
        "elec_ratio": round(elec / total, 3) if total else 0.0,
        "channels": dict(channels),
        "top_channel": top_channel,
    }


def timeline(items: Sequence[PerceptItem]) -> List[PerceptItem]:
    """按记录顺序保留，不做时间排序（日志本身有时间顺序，跨零点时字符串排序会错）。"""
    return list(items)


def _ratio(value: float) -> str:
    return "%.0f%%" % (value * 100)


def to_markdown(day_text: str, items: Sequence[PerceptItem], report: DayReport,
                date_label: str = "") -> str:
    """导出成可以直接贴进笔记或作文里的 Markdown 日报。"""
    stats = build_stats(items)
    lines: List[str] = []
    title = "感知日报" + ("｜" + date_label if date_label else "")
    lines.append("# " + title)
    lines.append("")
    if report.overview:
        lines.append("> " + report.overview.replace("\n", " "))
        lines.append("")

    lines.append("## 一、这一天接收了多少信息")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("| --- | --- |")
    lines.append("| 条目总数 | %d |" % stats["total"])
    lines.append("| 生物感官 | %d 条（%s） |" % (stats["bio"], _ratio(stats["bio_ratio"])))
    lines.append("| 电子感官 | %d 条（%s） |" % (stats["elec"], _ratio(stats["elec_ratio"])))
    lines.append("| 最高频通道 | %s |" % stats["top_channel"])
    lines.append("")

    channels: Dict[str, int] = stats["channels"]  # type: ignore[assignment]
    if channels:
        lines.append("通道分布：" + "，".join(
            "%s %d 条" % (name, count)
            for name, count in sorted(channels.items(), key=lambda kv: -kv[1])
        ))
        lines.append("")

    lines.append("## 二、信息时间轴")
    lines.append("")
    lines.append("| 时间 | 通道 | 来源 | 内容 | 细节 |")
    lines.append("| --- | --- | --- | --- | --- |")
    for item in timeline(items):
        detail = item.detail.replace("|", "／")
        lines.append("| %s | %s | %s | %s | %s |" % (
            item.time, item.channel, item.origin,
            item.content.replace("|", "／"), detail or "—",
        ))
    lines.append("")

    if report.comparison:
        lines.append("## 三、两种感官的对比")
        lines.append("")
        for index, card in enumerate(report.comparison, 1):
            lines.append("### %d. %s" % (index, card.title))
            lines.append("")
            lines.append(card.finding)
            if card.evidence:
                lines.append("")
                lines.append("> 依据：" + card.evidence)
            lines.append("")

    if report.suggestions:
        lines.append("## 四、可执行的三条建议")
        lines.append("")
        for index, suggestion in enumerate(report.suggestions, 1):
            lines.append("%d. %s" % (index, suggestion))
        lines.append("")

    if report.one_sentence:
        lines.append("## 五、一句话")
        lines.append("")
        lines.append("**" + report.one_sentence + "**")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("<details><summary>原始日志（点击展开）</summary>")
    lines.append("")
    lines.append(day_text.strip())
    lines.append("")
    lines.append("</details>")
    lines.append("")
    return "\n".join(lines)
