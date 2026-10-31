# -*- coding: utf-8 -*-
"""命令行入口：

    python -m perceptlog.cli analyze examples/day.txt -o 日报.md
    python -m perceptlog.cli analyze examples/day.txt --provider demo     # 不联网演示
    python -m perceptlog.cli chat examples/day.txt
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .config import PROVIDER_PRESETS, MissingCredential, Settings
from .report import build_stats, to_markdown


def _read(path: str) -> str:
    file = Path(path)
    if not file.exists():
        raise SystemExit("找不到文件：%s" % path)
    return file.read_text(encoding="utf-8")


def _settings_from_args(args: argparse.Namespace) -> Settings:
    base = Settings.from_env()
    overrides = {}
    if args.provider:
        preset = PROVIDER_PRESETS[args.provider]
        overrides["provider"] = args.provider
        overrides["base_url"] = args.base_url or preset["base_url"] or None
        overrides["model"] = args.model or preset["model"]
        overrides["api_key"] = os.getenv(preset["api_key_env"], preset["api_key_default"])
    if args.model:
        overrides["model"] = args.model
    if args.base_url:
        overrides["base_url"] = args.base_url
    if args.key:
        overrides["api_key"] = args.key
    return base.with_overrides(**overrides)


def _analyze(day_text: str, settings: Settings):
    """演示模式只依赖标准库，真实模式才去导入 LangChain。"""
    if settings.is_demo:
        from .demo import run_demo

        return run_demo(day_text)

    from .chains import analyze_day

    return analyze_day(day_text, settings)


def cmd_analyze(args: argparse.Namespace) -> int:
    day_text = _read(args.file)
    settings = _settings_from_args(args)
    try:
        items, report = _analyze(day_text, settings)
    except MissingCredential as exc:
        print("[配置缺失] %s" % exc, file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - 命令行要给出可读错误而不是堆栈
        print("[生成失败] %s" % exc, file=sys.stderr)
        return 1

    stats = build_stats(items)
    print("共解析 %d 条：生物感官 %d 条，电子感官 %d 条，最高频通道 %s"
          % (stats["total"], stats["bio"], stats["elec"], stats["top_channel"]))
    markdown = to_markdown(day_text, items, report, date_label=args.label)
    if args.out:
        Path(args.out).write_text(markdown, encoding="utf-8")
        print("已写入：%s" % args.out)
    else:
        print()
        print(markdown)
    return 0


def cmd_chat(args: argparse.Namespace) -> int:
    day_text = _read(args.file)
    settings = _settings_from_args(args)
    if settings.is_demo:
        print("演示模式不支持追问，请配置 --provider deepseek 或 ollama。", file=sys.stderr)
        return 2

    from langchain_core.messages import AIMessage, HumanMessage

    from .chains import build_chat_chain
    from .llm import build_llm

    try:
        items, _ = _analyze(day_text, settings)
        llm = build_llm(settings)
    except MissingCredential as exc:
        print("[配置缺失] %s" % exc, file=sys.stderr)
        return 2

    chain = build_chat_chain(llm, items)
    history: list = []
    print("已整理 %d 条感知条目。输入问题开始追问，输入 exit 退出。" % len(items))
    while True:
        try:
            question = input("\n你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if question.lower() in {"exit", "quit", "退出"}:
            return 0
        if not question:
            continue
        answer = chain.invoke({"history": history, "question": question})
        print("\n助手> " + answer)
        history.extend([HumanMessage(content=question), AIMessage(content=answer)])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="perceptlog",
        description="感官账本 PerceptLog：把一天的感知日志读成一张信息结构图。",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("file", help="感知日志文件（.txt/.md，UTF-8）")
        p.add_argument("--provider", choices=list(PROVIDER_PRESETS), default=None,
                       help="模型提供方：deepseek / openai / ollama / demo")
        p.add_argument("--model", default=None, help="模型名，例如 deepseek-chat、qwen2.5:7b")
        p.add_argument("--base-url", dest="base_url", default=None, help="OpenAI 兼容接口地址")
        p.add_argument("--key", default=None, help="API Key，也可以用环境变量")

    analyze = sub.add_parser("analyze", help="生成感知日报")
    common(analyze)
    analyze.add_argument("-o", "--out", default=None, help="输出 Markdown 路径")
    analyze.add_argument("--label", default="", help="日期标签，例如 2026-11-03")
    analyze.set_defaults(func=cmd_analyze)

    chat = sub.add_parser("chat", help="基于当天日志追问")
    common(chat)
    chat.set_defaults(func=cmd_chat)
    return parser


def main(argv: list | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
