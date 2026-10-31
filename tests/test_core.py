# -*- coding: utf-8 -*-
"""纯函数测试：不依赖大模型、不依赖网络。

    python tests/test_core.py      # 直接跑
    pytest tests/                  # 装了 pytest 也可以
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from perceptlog.demo import demo_answer, demo_extract, demo_report
from perceptlog.parsing import (ParseError, find_json_candidate, parse_items,
                                parse_report)
from perceptlog.report import build_stats, to_markdown
from perceptlog.schema import DayReport, PerceptItem


def test_find_json_candidate_with_fence_and_chatter():
    raw = '好的，结果如下：\n```json\n[{"a": 1}]\n```\n以上。'
    assert find_json_candidate(raw) == '[{"a": 1}]'


def test_parse_items_normalises_aliases():
    raw = '''```json
    [{"time": "7:05", "channel": "耳朵", "origin": "生物", "content": "垃圾车倒车", "detail": "嘀嘀嘀"}]
    ```
    '''
    items = parse_items(raw)
    assert len(items) == 1
    assert items[0].channel == "听觉"
    assert items[0].origin == "生物感官"


def test_parse_items_accepts_wrapped_object():
    raw = '{"items": [{"time": "8:00", "channel": "视觉", "origin": "电子感官", "content": "锁屏通知"}]}'
    items = parse_items(raw)
    assert items[0].content == "锁屏通知"


def test_parse_items_rejects_empty():
    try:
        parse_items("[]")
    except ParseError:
        return
    raise AssertionError("空数组应当报错")


def test_parse_items_skips_broken_entry():
    raw = '[{"channel": "视觉", "origin": "电子感官"}, {"content": "桂花味", "channel": "嗅觉", "origin": "生物感官"}]'
    items = parse_items(raw)
    assert len(items) == 1 and items[0].content == "桂花味"


def test_parse_report_coerces_string_cards():
    raw = '{"overview": "x", "comparison": ["很不一样"], "suggestions": ["少看手机"], "one_sentence": "y"}'
    report = parse_report(raw)
    assert isinstance(report, DayReport)
    assert report.comparison[0].finding == "很不一样"
    assert report.suggestions == ["少看手机"]


def test_stats_and_markdown():
    items = [
        PerceptItem(content="垃圾车", channel="听觉", origin="生物感官", time="7:05", detail="嘀嘀嘀"),
        PerceptItem(content="锁屏通知", channel="视觉", origin="电子感官", time="7:10"),
        PerceptItem(content="桂花味", channel="嗅觉", origin="生物感官", time="7:40"),
    ]
    stats = build_stats(items)
    assert stats["total"] == 3
    assert stats["bio"] == 2 and stats["elec"] == 1
    assert stats["top_channel"] == "听觉"

    report = DayReport(overview="今天偏电子。", suggestions=["把手机放远一点"], one_sentence="身体在场")
    markdown = to_markdown("原始日志", items, report, date_label="2026-11-03")
    assert "感知日报｜2026-11-03" in markdown
    assert "| 听觉 | 生物感官 | 垃圾车 | 嘀嘀嘀 |" in markdown
    assert "把手机放远一点" in markdown


def test_demo_pipeline_runs_without_model():
    text = Path(__file__).resolve().parents[1] / "examples" / "day.txt"
    day = text.read_text(encoding="utf-8")
    items = demo_extract(day)
    assert 5 <= len(items) <= 30
    assert any(item.origin == "生物感官" for item in items)
    assert any(item.origin == "电子感官" for item in items)

    report = demo_report(items)
    assert report.overview and report.comparison and len(report.suggestions) == 3

    answer = demo_answer("下午我漏掉了什么", items)
    assert "演示模式" in answer


def _run_all() -> None:
    passed = 0
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
            passed += 1
            print("PASS %s" % name)
    print("\n%d 项全部通过" % passed)


if __name__ == "__main__":
    _run_all()
