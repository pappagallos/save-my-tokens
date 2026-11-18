# Save My Tokens

[English](README.md) · [한국어](README.ko.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

从长日志中找出回答问题所需的原文，并按任务选择模型。分类在本地完成，无需调用模型。

![从问题出发，截取日志中的证据，再选一个模型回答。](docs/how-it-works.webp)

## 工作原理

1. 按关键词搜索整个文件，保留匹配段落和字节位置。默认最多输出 4,096 字节。用 `--at BYTE` 查看附近的原文。统计全部出现次数时应搜索完整文件。
2. 本地规则把请求分为简单提取、范围明确的任务、常规实现和深入推理，并从所选平台的模型中进行选择。在终端对日志使用 `--ask`，会把问题和摘录发送给 Codex。
3. 图中以 Sol 回答问题为例。普通任务执行一次。只有主动发起对比，才会执行两次并记录两份答案。

## 按平台安装

先克隆仓库，在仓库目录中运行安装命令。将 `/path/to/project` 改为现有项目的路径，将 `cursor` 改为表中的安装 ID。每个项目技能都自带 Python 脚本。重新打开项目后选择 `save-my-tokens`。

```sh
git clone https://github.com/pappagallos/save-my-tokens.git
cd save-my-tokens
python3 install.py --platform cursor --project /path/to/project
```

若要安装 Codex 原生插件，在仓库目录运行以下命令，然后新建对话。安装后请保留仓库目录。

```sh
codex plugin marketplace add .
codex plugin add save-my-tokens@save-my-tokens-local
codex plugin list --marketplace save-my-tokens-local --json
```

需要 Python 3.9 或更高版本和 Git。运行模型前，先安装所选平台的 CLI。可在 PATH 中的个人目录创建链接，然后从工作项目启动。

```sh
mkdir -p "$HOME/.local/bin"
ln -s "$PWD/save-my-tokens" "$HOME/.local/bin/save-my-tokens"
```

| 平台 | 安装 ID | 项目目录 | 终端模型选择 |
|---|---|---|---|
| Codex CLI | `codex` | `.agents/skills/` | CLI 模型列表 · `codex` |
| Claude Code | `claude` | `.claude/skills/` | 服务商别名 · `claude` |
| Cursor | `cursor` | `.cursor/skills/` | CLI 模型列表 · `agent` |
| Gemini CLI | `gemini` | `.gemini/skills/` | ACP 模型列表 · `gemini --acp` |
| Grok Build | `grok` | `.grok/skills/` | CLI 模型列表 · `grok` |
| GitHub Copilot | `copilot` | `.github/skills/` | ACP 模型列表 · `copilot --acp` |
| Devin | `devin` | `.devin/skills/` | ACP 模型列表 · `devin acp` |
| OpenCode | `opencode` | `.opencode/skills/` | ACP 模型列表 · `opencode acp` |
| Google Antigravity | `antigravity` | `.agent/skills/` | ACP 模型列表 · `agy_acp_server.par` |
| Kiro | `kiro` | `.kiro/skills/` | ACP 模型列表 · `kiro-cli acp` |
| TRAE | `trae` | `.trae/skills/` | ACP 模型列表 · `traecli acp serve` |
| TRAE China | `trae-cn` | `.trae-cn/skills/` | ACP 模型列表 · `traecli acp serve` |
| Qoder | `qoder` | `.qoder/skills/` | ACP 模型列表 · `qodercli --acp` |
| Mistral Vibe | `vibe` | `.vibe/skills/` | ACP 模型列表 · `vibe-acp` |
| Pi | `pi` | `.pi/skills/` | ACP 模型列表 · `pi-acp` |
| Hermes Agent | `hermes` | `.hermes/skills/` | ACP 模型列表 · `hermes acp` |
| DeepSeek Harness | `deepseek` | `.dsh/skills/` | ACP 模型列表 · `dsh --profile acp` |
| Oh My Pi | `omp` | `.omp/skills/` | ACP 模型列表 · `omp acp` |
| Replit Agent | `replit` | `.agents/skills/` | 手动选用外部引擎 |
| Rovo Dev | `rovodev` | `.rovodev/skills/` | 手动选用外部引擎 |
| Veto | `veto` | `.veto/skills/` | 手动选用外部引擎 |

ACP 是终端和编码助手之间的通信协议。终端通过它获取可用模型，并在发出问题前设置模型。请安装表中对应的程序并登录。项目技能也可以直接在编辑器中摘取原文。使用 Hermes 时，在项目内运行 `hermes skills trust`。安装后重启 Trae。若 Veto 只读取用户级技能，请使用 `--project "$HOME"`。

Claude 连续对话还需要 `claude-agent-acp`。ACP 程序必须公开可选模型。平台的工具权限继续生效。

表中列出技能安装目标。已使用实际账号验证 Codex 和 Claude Code 的回复，其余适配器通过模拟 CLI 或协议响应进行检查。

## 为每个请求选择模型

`route` 预览模型选择，`task` 执行一次请求，`chat` 保留同一会话并在每一轮重新选择模型。输入 `/exit` 退出。切换发生在启动器创建的会话中。已有编辑器对话的模型由编辑器管理。表中标记为外部引擎的平台需要在项目终端显式指定已登录的引擎，例如 `--engine codex`。

```sh
save-my-tokens route --engine codex '提取错误代码'
save-my-tokens task --engine claude '实现解析器'
save-my-tokens chat --engine codex
save-my-tokens build.log -q failure_code --ask '提取错误代码'
```

路由先选适合当前任务的模型系列，再选该系列在当前列表中版本号最高的模型。系列优先级由本项目的规则决定。账号、地区和 CLI 版本会影响列表。只有一个模型时，四个等级均使用它。Claude 单次执行使用服务商维护的 Haiku、Sonnet 和 Opus 别名。空列表会停止执行。可用 `--model ID` 指定模型，或用 `--tiers 轻量 聚焦 常规 深度` 自定义四个等级。简短的“继续”沿用上一等级。 [Codex](https://learn.chatgpt.com/docs/non-interactive-mode) · [Claude Code](https://code.claude.com/docs/en/model-config) · [Cursor](https://cursor.com/docs/cli/reference/parameters) · [Grok Build](https://docs.x.ai/build/cli/reference) · [Gemini](https://geminicli.com/docs/cli/model/) · [ACP](https://agentclientprotocol.com/protocol/v1/session-config-options) · [ACP registry](https://github.com/agentclientprotocol/registry)

下表是优先选择的模型系列。两个阶段可以使用同一模型。多服务商平台只选当前账号公开的模型。账号允许时可用 `--model fable` 显式选择 Claude Fable。预览别名显示的是传给服务商的名称，具体版本与计费条件由服务商决定。

| 任务 | 简单提取 | 范围明确的任务 | 常规实现 | 深入推理 |
| --- | --- | --- | --- | --- |
|  | 提取、翻译或简短摘要 | 检查截图或修改单个函数 | 实现功能、调试或重构 | 排查竞态、偶发数据丢失或跨服务故障 |
| Codex | Luna | Terra | Sol | Astra |
| Claude Code / Kiro | Haiku | Sonnet | Sonnet | Opus |
| Gemini / Antigravity | Flash-Lite | Flash | Flash | Pro |
| Cursor | Mini / Haiku | Composer / Terra | Sonnet / Sol | Opus / Astra |
| Grok Build | Non-reasoning / Fast | Build / Code | Build / Grok | Reasoning / Heavy / Grok |
| Copilot | Mini / Haiku | Terra / Flash | Sol / Sonnet | Astra / Opus |
| Devin | Haiku / Fast | SWE / Terra | Sonnet / Sol | Opus / Astra |
| Qoder | Efficient | Efficient | Performance / Fast | Ultimate |
| Mistral Vibe | Small / Mini | Devstral Small | Devstral / Medium | Large / Medium |
| DeepSeek Harness | Flash | Flash / Coder | Pro / Chat | Pro / Reasoner |
| TRAE / TRAE China | Flash / Mini | Coder / Seed | Sonnet / GLM / Qwen | Opus / Pro / Reasoner |
| OpenCode / Hermes / Pi / Oh My Pi | Luna / Haiku / Flash-Lite | Terra / Flash / Sonnet | Sol / Sonnet / Composer | Astra / Opus / Pro |

Replit 和 Rovo Dev 使用项目终端中明确指定的外部 CLI。Rovo 自带交互菜单 `/models`。对于 oleg-koval 的 Veto CLI，`task --host veto --engine codex` 会把所选模型传给 `veto start`。其他 Veto 产品可在终端直接选外部引擎。 [Devin](https://docs.devin.ai/cli/models) · [Copilot](https://docs.github.com/en/copilot/reference/ai-models/supported-models) · [OpenCode](https://opencode.ai/docs/models/) · [Qoder](https://docs.qoder.com/cli/model) · [DeepSeek](https://api-docs.deepseek.com/quick_start/pricing/) · [Mistral](https://docs.mistral.ai/models) · [Rovo](https://support.atlassian.com/rovo/docs/switch-between-large-language-models-in-rovo-dev-cli/) · [Veto](https://github.com/oleg-koval/veto)

```sh
save-my-tokens models --engine codex
save-my-tokens models --engine gemini
save-my-tokens models --engine qoder
save-my-tokens route --host replit --engine claude 'fix a typo'
```

## 逐题比较用量

用同一个文件和同一个问题执行 `compare`，会产生两次服务调用。有文件时默认使用相同模型，以比较摘录的效果。没有文件时，将常规模型与自动选择的模型进行比较。用 `--baseline-model` 更改基线。Codex 与 Claude Code 支持真实用量比较。所有平台都可使用 `measure` 在本地按 OpenAI 的 `o200k_base` 编码估算文本大小。

```sh
python3 experiments/benchmark.py --write-log /tmp/smt-example.log
question='Extract the missing key and failure code. Return both values.'
./save-my-tokens compare "$question" --file /tmp/smt-example.log -q failure_code \
  --expect SNAPSHOT_CLOCK --expect E7429 --out results.jsonl
./save-my-tokens compare --engine claude "$question" --file /tmp/smt-example.log -q failure_code
uv run --with tiktoken==0.12.0 -- ./save-my-tokens measure "$question" --file /tmp/smt-example.log -q failure_code
```

记录问题、两边的模型、输入、缓存输入、输出、总量、耗时、原始答案与预期文字是否出现。缓存输入已计入输入。节省量等于原始总量减去优化后总量，负数表示增加。`--out` 将问题和答案追加到指定本地文件。

## 实测结果

| 问题 | 模型 | 之前 → 之后（总量） | 降幅 | 答案 |
|---|---|---|---|---|
| 缺失的设置项与错误代码 | Luna | 21,259 → 16,243 | 23.59% | 均正确 |
| 模块 257 的耗时 | Luna | 21,262 → 16,249 | 23.58% | 均为 `15` |
| 缺失的设置项与错误代码 | Haiku 5.5 | 13,112 → 4,070 | 68.96% | 均正确 |
| 含义不清的单位名称问题 | Sol | 25,882 → 20,871 | 19.36% | 答案不同 |

各行均为同一份合成日志上的一组成对测试。对表述不清的问题，答案分别为 `milliseconds` 与 `module_257`。仅检查字符串无法判断哪一种解释符合提问者的本意。总量包含服务附加的提示。本实验没有测量订阅额度、费用或平均节省比例。换模型也会影响缓存复用。 [JSONL](experiments/observations.jsonl) · [v0.2.0 · 한국어](experiments/v0.2.ko.md)

## 研究与文档依据

Nature 上的 OpenScholar 研究评估了检索相关段落与标注来源的方法。npj Digital Medicine 的实验改变了证据在长文本中的位置。我们据此搜索整个文件，并保留原文偏移量。本工具使用字面匹配，日志上的效果由项目单独测量。 [Nature · OpenScholar](https://www.nature.com/articles/s41586-025-10072-4) · [npj Digital Medicine](https://www.nature.com/articles/s41746-025-01651-w) · [2025 JIF](https://www.nature.com/nature-portfolio/about-journals/journal-metrics)

Superpowers 先介绍工作流程与各客户端的安装方式。Context7 对比同一请求的结果。RTK 提供用量测量命令。Impeccable 在示例旁列出支持的平台。这里还公开了正确性检查和结果有分歧的案例。 [Superpowers](https://github.com/obra/superpowers) · [Context7](https://github.com/upstash/context7) · [RTK](https://github.com/rtk-ai/rtk) · [Impeccable](https://github.com/pbakaus/impeccable/tree/d41d9860b0094dcb68030657da63461212835aaa)

在本次找到且显示分数的 Codex 帖子中，一篇减少重复读取和冗长输出的经验帖为 +298 分，一篇将简单任务交给轻量模型的路由帖为 +21 分。11 月另有 Claude Code 的后续实验，比较不同任务的成本和正确性。分数是检索时的快照，结果取决于作者的工作负载。 [r/codex · +298](https://www.reddit.com/r/codex/comments/1tyxkzj/how_i_cut_codex_token_use_from_138mday_to_20mday/) · [r/codex · +21](https://www.reddit.com/r/codex/comments/1vdbi4s/luna_just_got_80_cheaper_so_i_rebuilt_my_codex/) · [r/ClaudeCode](https://www.reddit.com/r/ClaudeCode/comments/1xxyc5a/does_delegating_to_cheaper_models_actually_save/)
