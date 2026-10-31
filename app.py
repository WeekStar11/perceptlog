# -*- coding: utf-8 -*-
"""Streamlit 界面：左边配置模型，中间贴日志，右边看日报。

启动：streamlit run app.py
"""
from __future__ import annotations

from pathlib import Path
import os

import pandas as pd
import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage

from perceptlog.chains import analyze_day, build_chat_chain
from perceptlog.config import PROVIDER_PRESETS, Settings
from perceptlog.demo import demo_answer
from perceptlog.llm import MissingCredential, build_llm
from perceptlog.report import build_stats, to_markdown

SAMPLE_PATH = Path(__file__).parent / "examples" / "day.txt"

st.set_page_config(page_title="感官账本 PerceptLog", page_icon="🧠", layout="wide")


@st.cache_resource(show_spinner=False)
def cached_llm(provider: str, model: str, base_url: str, api_key: str, temperature: float):
    """同一个配置只建一次客户端，避免每轮对话都重新握手。"""
    settings = Settings(provider=provider, model=model, base_url=base_url or None,
                        api_key=api_key, temperature=temperature)
    return build_llm(settings)


def sidebar() -> Settings:
    st.sidebar.title("🧠 感官账本")
    st.sidebar.caption("把一天的感知日志，读成一张信息结构图")

    provider = st.sidebar.selectbox(
        "模型来源",
        options=list(PROVIDER_PRESETS),
        index=list(PROVIDER_PRESETS).index("deepseek"),
        format_func=lambda key: PROVIDER_PRESETS[key]["label"],
    )
    preset = PROVIDER_PRESETS[provider]
    st.sidebar.caption(preset["note"])

    model = st.sidebar.text_input("模型名", value=preset["model"], disabled=provider == "demo",
                                  key="model_" + provider)
    base_url = st.sidebar.text_input(
        "接口地址（OpenAI 兼容）", value=preset["base_url"], disabled=provider == "demo",
        key="base_url_" + provider,
    )
    api_key = st.sidebar.text_input(
        "API Key",
        value=os.getenv(preset["api_key_env"], preset["api_key_default"]),
        type="password",
        disabled=provider == "demo",
        key="api_key_" + provider,
    ) or preset["api_key_default"]
    temperature = st.sidebar.slider("温度", 0.0, 1.0, 0.3, 0.1,
                                    help="越低越稳，做结构化抽取建议 0.2–0.4")

    st.sidebar.divider()
    if provider == "ollama":
        st.sidebar.info("离线使用：先 `ollama serve`，再 `ollama pull qwen2.5:7b`。")
    if provider == "demo":
        st.sidebar.warning("演示模式不调用大模型，只用于预览界面与导出格式。")

    return Settings(provider=provider, model=model, base_url=base_url or None,
                    api_key=api_key, temperature=temperature)


def show_stats(items) -> None:
    stats = build_stats(items)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("条目总数", stats["total"])
    col2.metric("生物感官", stats["bio"], "%.0f%%" % (stats["bio_ratio"] * 100))
    col3.metric("电子感官", stats["elec"], "%.0f%%" % (stats["elec_ratio"] * 100))
    col4.metric("最高频通道", stats["top_channel"])

    frame = pd.DataFrame(
        [{"来源": item.origin, "通道": item.channel, "条数": 1} for item in items]
    )
    left, right = st.columns(2)
    with left:
        st.caption("通道分布")
        channel_counts = (frame.groupby("通道")["条数"].sum()
                          .sort_values(ascending=False).reset_index())
        st.bar_chart(channel_counts, x="通道", y="条数")
    with right:
        st.caption("来源对比")
        origin_counts = frame.groupby("来源")["条数"].sum().reset_index()
        st.bar_chart(origin_counts, x="来源", y="条数")


def show_report(items, report, day_text, label: str) -> None:
    show_stats(items)

    st.subheader("这一天的判断")
    st.write(report.overview)

    for card in report.comparison:
        with st.container(border=True):
            st.markdown("**%s**" % card.title)
            st.write(card.finding)
            if card.evidence:
                st.caption("依据：" + card.evidence)

    st.subheader("三条建议")
    for index, suggestion in enumerate(report.suggestions, 1):
        st.markdown("%d. %s" % (index, suggestion))

    if report.one_sentence:
        st.success(report.one_sentence)

    with st.expander("查看全部条目"):
        st.dataframe(
            pd.DataFrame([item.to_dict() for item in items]),
            use_container_width=True, hide_index=True,
        )

    markdown = to_markdown(day_text, items, report, date_label=label)
    st.download_button("下载 Markdown 日报", data=markdown,
                       file_name="感知日报_%s.md" % (label or "今天"),
                       mime="text/markdown")


def show_chat(settings: Settings) -> None:
    items = st.session_state.get("items") or []
    if not items:
        return

    st.subheader("追问这份日志")
    st.caption("例如：我这一天最亏的是什么？下午哪段时间完全没留下记忆？")

    for message in st.session_state.get("messages", []):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    question = st.chat_input("问点什么……")
    if not question:
        return

    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    st.session_state["messages"].append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        if settings.is_demo:
            answer = demo_answer(question, items)
            st.markdown(answer)
        else:
            try:
                llm = cached_llm(settings.provider, settings.model, settings.base_url or "",
                                 settings.api_key, settings.temperature)
                chain = build_chat_chain(llm, items)
                history = []
                for message in st.session_state["messages"][:-1]:
                    cls = HumanMessage if message["role"] == "user" else AIMessage
                    history.append(cls(content=message["content"]))
                answer = st.write_stream(chain.stream({"history": history,
                                                       "question": question}))
            except MissingCredential as exc:
                answer = "还没有配置 API Key：%s" % exc
                st.error(answer)
            except Exception as exc:  # noqa: BLE001
                answer = "调用模型失败：%s" % exc
                st.error(answer)
    st.session_state["messages"].append({"role": "assistant", "content": answer})


def main() -> None:
    settings = sidebar()

    st.title("一天的感知，到底被谁拿走了？")
    st.write(
        "把这一天你**接收到的信息**随手记下来——几点、在哪里、看到了什么、听到了什么、"
        "闻到了什么、身体什么感觉、手机弹了什么。不用讲究文采，越具体越好。"
        "下面的助手会把它拆成条目、算出结构，再告诉你这一天的感知被什么占满了。"
    )

    col_a, col_b = st.columns([1, 1])
    with col_b:
        if SAMPLE_PATH.exists() and st.button("载入示例日志", use_container_width=True):
            for key in ("items", "report", "messages"):
                st.session_state.pop(key, None)
            st.session_state["day_text"] = SAMPLE_PATH.read_text(encoding="utf-8")
            st.rerun()

    if "day_text" not in st.session_state:
        st.session_state["day_text"] = ""
    day_text = st.text_area("今天的记录", key="day_text", height=320,
                            placeholder="7:05 闹钟响之前被楼下垃圾车的倒车声弄醒……")

    label = st.text_input("日期标签（可选）", placeholder="2026-11-03")

    if st.button("生成感知日报", type="primary"):
        if len(day_text.strip()) < 20:
            st.warning("至少写几句再生成，否则拆不出条目。")
        else:
            with st.spinner("正在读这一天的信息……"):
                try:
                    items, report = analyze_day(day_text, settings)
                except MissingCredential as exc:
                    st.error("还没有配置 API Key：%s\n\n也可以先把模型来源切到「本地演示模式」看看效果。" % exc)
                    return
                except Exception as exc:  # noqa: BLE001
                    st.error("生成失败：%s" % exc)
                    return
            st.session_state["items"] = items
            st.session_state["report"] = report
            st.session_state["messages"] = []
            st.rerun()

    if st.session_state.get("items") and st.session_state.get("report"):
        st.divider()
        show_report(st.session_state["items"], st.session_state["report"],
                    st.session_state.get("day_text", day_text), label)
        st.divider()
        show_chat(settings)


if __name__ == "__main__":
    main()



