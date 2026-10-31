# -*- coding: utf-8 -*-
"""本地演示模式：不用大模型，用关键词规则跑通同样的流程。

它不是“智能”的替代品，只是为了让界面、导出、统计在没有网络、没有 API Key 时也能演示。
README 里明确写了它的定位：仅用于预览，正式使用请配置真实模型。
"""
from __future__ import annotations

import re
from typing import List, Tuple

from .report import build_stats
from .schema import DayReport, InsightCard, PerceptItem

# 判断“这条信息必须经过设备转译才能到达”的关键词（强规则）
ELECTRONIC_HINTS = (
    "屏幕", "锁屏", "耳机", "平板", "手环", "播客", "相册", "取件码", "电脑",
    "通知", "推送", "微信", "群消息", "短信", "邮件", "直播", "弹幕", "导航",
    "短视频", "朋友圈", "剧", "视频", "扫码", "二维码",
)
# 弱规则：出现“手机”时，还要同时出现下列词才算电子感官，避免“放下手机听见猫叫”被判错
WEAK_ELECTRONIC = ("手机",)
WEAK_CONFIRM = ("通知", "消息", "刷", "亮", "看", "响", "弹", "响铃", "震")

CHANNEL_HINTS = (
    ("嗅觉", ("闻", "气味", "香", "臭", "桂花", "油烟", "味道")),
    ("味觉", ("尝", "咸", "甜", "辣", "酸", "口感", "豆浆", "油条")),
    ("听觉", ("听", "声", "响", "叫", "喊", "哨", "嗡", "噪", "播客", "电话", "敲", "聊", "说", "讲", "嘀")),
    ("触觉", ("摸", "凉", "烫", "黏", "硬", "软", "触", "勒", "重量", "压手", "风")),
    ("本体觉", ("累", "困", "饿", "腰", "酸", "心跳", "发涩", "肿", "烦")),
    ("设备推送", ("通知", "推送", "提醒", "弹窗", "消息", "微信", "群")),
    ("视觉", ("看", "屏幕", "亮", "投影", "照片", "视频", "字", "图", "剧", "路", "镜")),
)

_TIME_RE = re.compile(r"(\d{1,2}[:：]\d{2})")
_QUOTE_RE = re.compile(r"[“\"]([^”\"]{2,30})[”\"]")
_DATE_RE = re.compile(r"^\s*\d{4}[-/.]\d{1,2}[-/.]\d{1,2}")


def _is_header(sentence: str) -> bool:
    """跳过“2026-11-03 星期二，我的感知记录”这类抬头。"""
    if not _DATE_RE.match(sentence):
        return False
    stripped = _DATE_RE.sub("", sentence)
    for word in ("星期", "周", "的感知记录", "记录"):
        stripped = stripped.replace(word, "")
    return len(stripped.strip(" ，,、。")) < 4


def _strip_time(sentence: str) -> str:
    """去掉句首的时刻，避免正文里重复出现“7:00 7:00 …”。"""
    match = re.match(r"^\s*(\d{1,2}[:：]\d{2})\s*[，,、:：]?\s*", sentence)
    if match:
        return sentence[match.end():].strip()
    return sentence


def _guess_time(sentence: str, fallback: str) -> str:
    match = _TIME_RE.search(sentence)
    if match:
        return match.group(1).replace("：", ":")
    for period in ("早上", "上午", "中午", "下午", "傍晚", "晚上", "夜里", "睡前"):
        if period in sentence:
            return period
    return fallback


def _guess_channel(sentence: str) -> str:
    for channel, words in CHANNEL_HINTS:
        if any(word in sentence for word in words):
            return channel
    return "视觉"


def _split_sentences(text: str) -> List[str]:
    chunks = re.split(r"[。；;\n]", text)
    sentences = []
    for chunk in chunks:
        chunk = chunk.strip(" ，,、")
        if len(chunk) < 6 or _is_header(chunk):
            continue
        sentences.append(chunk)
    return sentences


def demo_extract(day_text: str, limit: int = 24) -> List[PerceptItem]:
    """把日志切成句子，逐句猜通道与来源。"""
    items: List[PerceptItem] = []
    last_time = ""
    for index, raw in enumerate(_split_sentences(day_text)[:limit]):
        sentence = _strip_time(raw)
        strong = any(word in sentence for word in ELECTRONIC_HINTS)
        weak = any(word in sentence for word in WEAK_ELECTRONIC) and any(
            word in sentence for word in WEAK_CONFIRM
        )
        quote = _QUOTE_RE.search(sentence)
        time = _guess_time(raw, last_time or "第%d段" % (index + 1))
        if re.match(r"^\s*\d{1,2}[:：]\d{2}", raw):
            last_time = time
        items.append(PerceptItem(
            time=time,
            channel=_guess_channel(sentence),
            origin="电子感官" if (strong or weak) else "生物感官",
            content=sentence[:28] + ("…" if len(sentence) > 28 else ""),
            detail=quote.group(1) if quote else "",
        ))
    return items


def demo_report(items: List[PerceptItem]) -> DayReport:
    """用模板生成一份可读的分析，数字来自真实统计。"""
    stats = build_stats(items)
    top_channel = stats["top_channel"]
    elec_share = int(stats["elec_ratio"] * 100)
    overview = (
        "这一天共整理出 %d 条信息，其中电子感官 %d 条（%d%%）、生物感官 %d 条，"
        "出现最多的通道是%s。%s"
        % (
            stats["total"], stats["elec"], elec_share, stats["bio"], top_channel,
            "整体上设备转译的信息已经超过身体直接接收的信息。"
            if stats["elec"] > stats["bio"] else "身体直接接收的信息仍占多数。",
        )
    )

    elec_items = [item for item in items if item.origin == "电子感官"]
    bio_items = [item for item in items if item.origin == "生物感官"]
    evidence_elec = "；".join(
        "%s %s" % (item.time, item.content) for item in elec_items[:2]
    ) or "这一天没有明显的电子感官条目"
    evidence_bio = "；".join(
        "%s %s" % (item.time, item.content) for item in bio_items[:2]
    ) or "这一天没有明显的生物感官条目"

    cards = [
        InsightCard(
            title="通道与带宽",
            finding="电子感官看起来通道很多，最后落到身上的基本只有屏幕和耳机两个出口；"
                    "生物感官的嗅觉、味觉、触觉在这份日志里仍然是设备替不了的部分。",
            evidence=evidence_bio,
        ),
        InsightCard(
            title="谁来筛选",
            finding="生物感官靠生理适应自动过滤恒定刺激，电子感官靠算法排序决定先给你看什么。"
                    "同样的时间里，后者替你做了更多的取舍。",
            evidence=evidence_elec,
        ),
        InsightCard(
            title="精度与留存",
            finding="设备记得更准、更全，却不一定记得住；身体记得更糊，但更容易在事后被一句话、一个气味唤回来。",
            evidence="电子条目 %d 条，生物条目 %d 条" % (len(elec_items), len(bio_items)),
        ),
    ]

    suggestions = [
        "把睡前 30 分钟设为无屏幕时段，手机放到伸手够不到的地方，只留纸和笔。",
        "吃饭时把手机扣在桌上，先吃三口再决定要不要看视频，至少完整尝出一道菜的咸淡。",
        "白天挑一个整点，摘掉耳机走五分钟，只记录听到的三种声音和闻到的一种气味。",
    ]
    one_sentence = "身体在场的时间，才是信息真正留下来的时间。"

    return DayReport(
        overview=overview,
        comparison=cards,
        suggestions=suggestions,
        one_sentence=one_sentence,
    )


def run_demo(day_text: str) -> Tuple[List[PerceptItem], DayReport]:
    items = demo_extract(day_text)
    return items, demo_report(items)


def demo_answer(question: str, items: List[PerceptItem]) -> str:
    """演示模式下的“追问”：按二元字片段重合度找最相关的条目。"""
    stats = build_stats(items)
    grams = {question[i:i + 2] for i in range(max(1, len(question) - 1)) if question[i:i + 2].strip()}
    scored = []
    for item in items:
        haystack = item.content + item.detail
        score = sum(1 for gram in grams if gram in haystack)
        if score:
            scored.append((score, item))
    scored.sort(key=lambda pair: -pair[0])

    head = "（演示模式：按关键词匹配，不是大模型回答）"
    if not scored:
        return (head + "\n\n日志里没有和这个问题直接相关的条目。这一天共 %d 条，"
                "最高频通道是%s。" % (stats["total"], stats["top_channel"]))

    lines = [head, "", "最相关的几条："]
    for _, item in scored[:3]:
        lines.append("- %s｜%s｜%s%s" % (
            item.time, item.origin, item.content,
            ("（%s）" % item.detail) if item.detail else "",
        ))
    lines.append("")
    lines.append("配置真实模型后，这里会给出结合统计的完整分析。")
    return "\n".join(lines)

