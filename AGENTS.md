# AGENTS.md — Agent-Pilot V1 项目级 Agent 指令

> 本文件遵循 Claude Code / OpenAI Agents SDK / Cursor 的 `AGENTS.md` cascade 约定。
> 当 AI Agent（含 Cursor / Claude Code / Codex / Trae）在本仓库工作时，应当先读这份文件。

## 1. 项目身份

- **名称**: Agent-Pilot V1
- **定位**: 飞书 IM 中的 AI 主驾驶 Harness——把"群聊讨论 → 文档 → 画布 → PPT + 演讲稿"压成 90 秒一键交付，并保证手机/电脑/Web 三端实时一致
- **赛事**: 飞书 AI 校园挑战赛 · 基于 IM 的办公协同智能助手赛道
- **核心理念**: AI Agent 为主驾驶，GUI 为副驾驶（仪表盘 + 辅助操作台）

## 2. 5 层 Harness 架构（必须遵守）

V1 严格按 Modern Agent Harness Blueprint 2026 的 5 层组织代码：

| 层 | 目录 | 职责 | 不允许做什么 |
|---|---|---|---|
| **Runtime** | `pilot/runtime/` | 8 步 Claude Code harness loop / 状态机 / 检查点 / 中断恢复 | 不直接调用 LLM、不直接读写飞书 |
| **Context** | `pilot/context/` | append-only 事件日志 / ContextPack / filesystem working memory / AGENTS.md cascade | 不知道任何工具的存在 |
| **Capability** | `pilot/capability/` | 工具 / Skills / Workforce / MCP 客户端 | 不直接处理用户输入、不持有会话状态 |
| **Governance** | `pilot/governance/` | 4 级权限策略 / owner_lock / 沙箱 / 审计 / OTel | 不实现业务逻辑、不调用 LLM |
| **Surface** | `pilot/surface/` | 飞书 IM / Web Dashboard / Flutter / MCP server / ACP server | 不实现 Agent 决策逻辑 |

依赖方向：`Surface → Runtime → Context / Capability / Governance`，**禁止反向依赖**。

## 3. 6 大铁律（来自 Modern Agent Harness Blueprint 2026）

1. **Harness > Loop**：差异化在 Runtime + Context + Governance + Surface，不在 model-tool loop
2. **Cache stability first**：system prompt 用 `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` 切两段，append-only history
3. **Filesystem as working memory**：大段 markdown / 7000+ 字内容用 `artifact://...` handle，不塞 conversation
4. **Small stable action space**：原生工具控制在 8 个以内（doc / canvas / slide / archive / voice / bitable / sub_agent / ask_user）
5. **Subagents for context isolation**：用 sub-agent **不是因为多 Agent 听起来高级**，是因为需要独立 context 窗口
6. **Guardrails in runtime, not in prompt**：destructive tool 必须经 Governance 4 级权限（deny → allow → classifier → ask）

## 4. Cognition「单线程写」原则

- **Researcher / Critic 只读**：不修改任何 artifact，仅产 JSON 报告
- **Writer 单线程独占**：所有"写"动作只能由 Writer 一个串行做
- **Presenter 是无状态格式化器**：把 Writer 产出转 .pptx / 画布，不二次生成内容

## 5. 工具/技能优先级（写代码时遵守）

读文件用 `Read`，不用 `cat`。
搜文件用 `Glob`/`Grep`，不用 `find`/`rg`。
编辑文件用 `Edit`/`StrReplace`，不用 `sed`/`awk`。
shell 工具仅用于 git / npm / docker / systemctl 等真正需要 shell 的命令。

## 6. 飞书生态接入约定

- IM/Doc/Drive/Bitable/Card 全部走 `lark-oapi`，不要自己 HTTP
- Card 用 CardKit 2.0 streaming（`streaming_mode=true / print_frequency_ms=70`）
- 多维表格作为「关联文档/历史项目资料」上下文源（PRD §7.1）
- 反向暴露：`pilot/surface/mcp_server.py` 让 Cursor / Claude / Trae 调用 V1
- 工具集：`pilot/capability/skills/lark-cli-skills/` 软链或 git submodule 接入 `larksuite/cli` 的 29 SKILL

## 7. 测试约定

- 单元 mocked LLM：`tests/unit/`
- 裁判级 e2e：`tests/competition/`，5 条用例必须 < 30 秒（mocked）
- 真 LLM e2e：`AGENT_PILOT_REAL_LLM=1 pytest tests/competition/`

## 8. 提交约定

- 提交信息用中文 + 英文混排，格式 `[<层>] <动作>: <说明>`
- 例：`[runtime] feat: 实现 8 步 harness loop`
- 不在 commit message 中放秘钥

## 9. 文档地图

- `docs/JUDGE_GUIDE.md` — 裁判 5 分钟验收
- `docs/ARCHITECTURE.md` — 架构详解（含 Claude Code 8 步 / 5 层 Harness 映射）
- `docs/PRD_COVERAGE.md` — 队友 3 份 PRD 100% 对照
- `docs/HARNESS_DESIGN.md` — Harness 工程设计专题
- `docs/DEMO_SCRIPT.md` — 答辩演讲稿

## 10. 如果你是 AI 在改这个项目

1. 先读 `docs/ARCHITECTURE.md` 找到目标层
2. 读对应层的 `__init__.py` 看模块边界
3. 读 `tests/` 对应文件理解契约
4. 改代码 + 测试同时进行
5. 不要打破层依赖方向
6. 不要把 v13 的旧代码搬过来，要按 Harness 思维重写
