# 感官账本 PerceptLog

> 把一天的感知日志，读成一张信息结构图。

**基于 LangChain 的智能应用**：给它一段“我今天都接收到了什么”的流水账，它会拆出信息条目、算出通道结构、写出一份带依据的感知日报，并且可以就这一天继续追问。

在线模型（DeepSeek / OpenAI）与离线模型（Ollama）都支持，换一个 `base_url` 就能切换，不需要改代码。

开源仓库：`https://github.com/<你的GitHub用户名>/perceptlog`

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![LangChain](https://img.shields.io/badge/LangChain-LCEL-1C3C3C)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 目录

- [为什么做这个](#为什么做这个)
- [它做了什么](#它做了什么)
- [快速开始](#快速开始)
- [三种模型怎么选](#三种模型怎么选)
- [使用方式](#使用方式)
- [一次真实运行的样子](#一次真实运行的样子)
- [技术架构](#技术架构)
- [代码导览](#代码导览)
- [几个设计决定](#几个设计决定)
- [测试](#测试)
- [常见问题](#常见问题)
- [已知局限](#已知局限)
- [目录结构](#目录结构)
- [开源协议](#开源协议)

---

## 为什么做这个

《现代生活的信息感知》这门课里有一个很直接的观察：我们每天接收的信息，一部分来自自己的身体（看见、听见、闻到、尝到、摸到、以及饿和困），另一部分来自设备（屏幕、耳机、推送、手环）。后者越来越多，前者越来越少，但人对这件事几乎没有量化的感觉。

“我今天刷了很久手机”是一种模糊的自我指控。它能被说清楚的方式是：**把这一天收到的东西一条条列出来，再按通道和来源分类**。这件事人做起来很枯燥，机器做起来很合适——但机器不能替你回忆，所以流程被设计成“你随手记，它负责整理和判读”。

于是有了这个应用：输入是一段谁都能写的流水账，输出是一份能直接放进作业、周记或者日记里的结构化日报。

## 它做了什么

| 能力 | 说明 |
| --- | --- |
| 条目抽取 | 把口语化的流水账拆成一条条信息，标注时间、通道（视觉/听觉/嗅觉/味觉/触觉/本体觉/设备推送）、来源（生物感官/电子感官） |
| 结构统计 | 统计条目总数、两类来源的占比、各通道分布，并画成图 |
| 对比分析 | 从“通道与带宽、精度与留存、筛选权、时间性、身体感”里挑最有话可说的维度写对比，每条都要引用具体条目作为依据 |
| 行动建议 | 给 3 条当天就能执行的具体动作，落到时间点和动作上，不写“少玩手机”这种口号 |
| 追问对话 | 基于当天条目回答“我这一天最亏的是什么”“下午哪段完全没留下记忆”，回答必须引用条目，日志里没有就说没有 |
| 导出 | 一键导出 Markdown 日报，可折叠附上原始日志 |
| 双模式 | 在线模型 / 本地 Ollama 离线模型；另有不调用模型的“演示模式”，断网也能跑通界面 |

## 快速开始

### 1. 准备环境

需要 Python 3.10 及以上。

```bash
git clone https://github.com/<你的GitHub用户名>/perceptlog.git
cd perceptlog

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. 配置模型

```bash
cp .env.example .env
```

打开 `.env`，至少填一个 API Key。以 DeepSeek 为例：

```ini
PERCEPTLOG_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-你的key
PERCEPTLOG_MODEL=deepseek-chat
```

> 没有 Key 也能先跑：把 `PERCEPTLOG_PROVIDER` 改成 `demo`，界面和数据流都能走通，只是分析文字来自模板而不是大模型。

### 3. 启动

```bash
streamlit run app.py
```

浏览器打开终端里给出的地址（默认 `http://localhost:8501`），把日志粘进去，点“生成感知日报”。

命令行同样可用：

```bash
# 生成一份 Markdown 日报
python -m perceptlog.cli analyze examples/day.txt -o 感知日报.md --label 2026-11-03

# 只追问，不导出
python -m perceptlog.cli chat examples/day.txt

# 不联网演示
python -m perceptlog.cli analyze examples/day.txt --provider demo
```

## 三种模型怎么选

| 提供方 | 配置 | 是否需要联网 | 说明 |
| --- | --- | --- | --- |
| DeepSeek | `PERCEPTLOG_PROVIDER=deepseek`<br>`DEEPSEEK_API_KEY=sk-...` | 是 | 国内直连，价格低，中文表达自然，默认选项 |
| OpenAI | `PERCEPTLOG_PROVIDER=openai`<br>`OPENAI_API_KEY=sk-...` | 是 | 质量稳定，需要可访问 OpenAI 的网络 |
| Ollama | `PERCEPTLOG_PROVIDER=ollama`<br>`PERCEPTLOG_MODEL=qwen2.5:7b` | 否 | 完全离线：`ollama serve` + `ollama pull qwen2.5:7b`，数据不出本机 |
| 演示模式 | `PERCEPTLOG_PROVIDER=demo` | 否 | 关键词规则，仅用于预览界面与导出格式 |

三者共用同一套 `ChatOpenAI` 客户端（OpenAI 兼容协议），所以切换只是改 `base_url` 和模型名，链、提示词、解析器一行都不用动。

## 使用方式

1. **写日志**：越具体越好。时刻、地点、你看到/听到/闻到/尝到/摸到了什么、身体是什么感觉、手机弹了什么。不用讲究文采。
2. **生成日报**：点击生成后大约 5–15 秒（取决于模型），得到条目表、通道分布图、对比卡片和三条建议。
3. **追问**：在下方输入框继续问，比如“哪一段我完全没记住”“我这一天被算法决定了多少次”。
4. **导出**：下载 Markdown，粘进笔记或作业里。

日志建议控制在 500–2000 字、8–30 条信息。太短的日志拆不出结构，太长的会被截断到 12000 字。

## 一次真实运行的样子

输入 `examples/day.txt`（示例日志，20 条），演示模式的输出保存在 [examples/demo_report.md](examples/demo_report.md)，节选：

```markdown
# 感知日报｜2026-11-03

## 一、这一天接收了多少信息

| 指标 | 数值 |
| --- | --- |
| 条目总数 | 20 |
| 生物感官 | 12 条（60%） |
| 电子感官 | 8 条（40%） |
| 最高频通道 | 听觉 |

通道分布：听觉 10 条，视觉 3 条，本体觉 2 条，嗅觉 2 条，设备推送 1 条，味觉 1 条，触觉 1 条

## 三、两种感官的对比

### 1. 通道与带宽

电子感官看起来通道很多，最后落到身上的基本只有屏幕和耳机两个出口；
生物感官的嗅觉、味觉、触觉在这份日志里仍然是设备替不了的部分。

> 依据：7:00 闹钟响之前其实已经醒了一次，对面床的室友翻身，床架吱呀一…；
> 7:00 楼下垃圾清运车倒车，嘀、嘀、嘀从窗缝里挤进来
```

换成 DeepSeek 之后，同样的日志会得到更像“人写的”对比段落，并且每张卡片的依据会直接引用你日志里的原话。

## 技术架构

```
                 ┌──────────────────────────────┐
  你粘贴的日志 ──▶│  ChatPromptTemplate(extract) │
                 └──────────────┬───────────────┘
                                ▼
                        ChatOpenAI (LCEL)
                                ▼
                     StrOutputParser → 容错 JSON 解析
                                ▼
                    List[PerceptItem]  ←── 通道/来源归一化
                                ▼
        ┌───────────────────────┴────────────────────────┐
        ▼                                                ▼
  build_stats()（纯函数）                    ChatPromptTemplate(analyze)
  占比 / 通道分布 / 最高频通道                          ▼
        │                                       ChatOpenAI → 解析
        └──────────────┬──────────────────────────────┘
                       ▼
                  DayReport（对比卡片 + 建议 + 一句话）
                       ▼
            Markdown 导出 / Streamlit 渲染 / 追问链
```

整条链是 LCEL 组合出来的，没有 Agent、没有黑盒：

```python
chain = prompt | llm | StrOutputParser() | RunnableLambda(parse_items)
items = chain.invoke({"log": day_text})

report = (analyze_prompt | llm | StrOutputParser() | RunnableLambda(parse_report)) \
         .invoke({"payload": build_payload(items)})
```

追问链把当天的条目 JSON 和统计结果塞进 system 消息，再拼上对话历史：

```python
prompt = ChatPromptTemplate.from_messages([
    ("system", CHAT_SYSTEM),
    MessagesPlaceholder("history"),
    ("human", "{question}"),
]).partial(digest=digest, stats=stats_text)
```

## 代码导览

| 文件 | 作用 |
| --- | --- |
| `app.py` | Streamlit 界面：模型配置、日志输入、统计图、报告、追问、导出 |
| `perceptlog/cli.py` | 命令行：`analyze` 与 `chat` 两个子命令 |
| `perceptlog/chains.py` | 三条 LCEL 链：抽取、分析、追问 |
| `perceptlog/prompts.py` | 全部提示词，集中管理，方便对照修改 |
| `perceptlog/parsing.py` | 容错 JSON 解析：剥代码块、括号配平、修尾逗号 |
| `perceptlog/schema.py` | 数据结构与归一化（同义词 → 固定枚举） |
| `perceptlog/report.py` | 纯函数统计 + Markdown 导出 |
| `perceptlog/demo.py` | 规则版演示模式（关键词分类 + 模板报告） |
| `perceptlog/config.py` | 配置与提供方预设 |
| `tests/test_core.py` | 不依赖模型、不依赖网络的 8 项测试 |

## 几个设计决定

**为什么不直接上向量库做 RAG。** 一份日报只有二三十条、两三千字，塞进上下文绰绰有余。上向量库只会把一个“整理”问题变成一个“检索不准”的问题，还多一个部署负担。真要做长期日志（几十天）时再加检索也不迟，接口已经留好了。

**为什么手写解析而不是用 `with_structured_output`。** 各家 OpenAI 兼容接口对 `response_format` 的支持参差不齐，Ollama 的小模型尤其容易翻车。所以用“提示词约束 + 容错解析”这条路：剥掉代码块、括号配平、去掉尾逗号，再逐条校验，坏一条丢一条，不至于整份报废。

**为什么有演示模式。** 作业要能演示，而演示现场不一定有网、有 Key。演示模式用关键词规则跑通同样的数据流，输出的统计和文件格式与真实模型完全一致，界面不会因为没 Key 变成一块死板。它不假装自己是智能的——界面上、README 里都写明了。

**温度 0.3。** 这是一个信息抽取任务，需要稳定而不是发散；分析部分在同一份日志上略有差异是可接受的。

**通道里为什么有“设备推送”。** 推送本身不是一种感官，但它是“算法替你决定先看什么”最直接的证据，单独留一个通道，统计时才看得见。

## 测试

```bash
python tests/test_core.py     # 不需要安装大模型，直接跑
# 或者
pytest tests/
```

覆盖：代码块剥离、别名归一化、坏条目跳过、对比卡片容错、统计与 Markdown 导出、演示模式端到端。

## 常见问题

**Q：报 `MissingCredential` / 提示没有 API Key。**
`.env` 没生效或变量名写错。确认 `.env` 与 `app.py` 在同一层目录，变量名是 `DEEPSEEK_API_KEY` / `OPENAI_API_KEY`，改完重启一次 `streamlit run`。

**Q：Ollama 连不上。**
先确认 `ollama serve` 在跑，`ollama list` 里有对应模型，然后把 `PERCEPTLOG_BASE_URL` 设成 `http://localhost:11434/v1`（注意结尾的 `/v1`）。

**Q：模型输出解析失败。**
换个模型或把温度调到 0.1 再试；小参数模型（3B 以下）经常写不出合法 JSON，建议至少 7B。解析器已经做了大部分容错，仍失败时命令行会打印具体原因。

**Q：生成很慢。**
一次生成包含两次模型调用，DeepSeek 通常 5–15 秒；本地 7B 模型在无 GPU 的机器上可能要 1–2 分钟，属于正常。

**Q：我的日志会被上传吗？**
用在线模型时会发给你配置的服务商；用 Ollama 或演示模式时不出本机。项目本身不做任何额外上报，也不保存日志。

## 已知局限

- 一次只处理一天的日志，跨天对比还没做；
- 时间信息依赖日志里写出来的时刻，没写就只能标“未标注”；
- 小模型对“本体觉”和“设备推送”这两个通道的区分不稳定；
- 演示模式的分类是关键词规则，只保证流程跑通，不保证判断准确；
- 没有做多用户与持久化存储，刷新页面数据就没了。

后续想做的：多天趋势图、语音输入、按小时生成“注意力曲线”、把日报直接导出成 Word/PDF。

## 目录结构

```
perceptlog/
├── app.py                  # Streamlit 入口
├── requirements.txt
├── .env.example
├── LICENSE
├── perceptlog/
│   ├── __init__.py
│   ├── config.py           # 配置与提供方预设
│   ├── schema.py           # 条目 / 卡片 / 日报
│   ├── prompts.py          # 提示词
│   ├── chains.py           # LCEL 链
│   ├── parsing.py          # 容错 JSON 解析
│   ├── report.py           # 统计与 Markdown 导出
│   ├── demo.py             # 规则版演示模式
│   ├── llm.py              # 模型工厂
│   └── cli.py              # 命令行
├── examples/
│   ├── day.txt             # 示例日志
│   └── demo_report.md      # 示例输出
└── tests/
    └── test_core.py
```

## 开源协议

[MIT](LICENSE) © 2026 周星宇

---

<sub>本项目为《现代生活的信息感知》第七章“智能应用开发”作业，选题来自课程中的“生物感官与电子感官”对照。</sub>
