# Agent-Pilot V1 · PRD 100% 覆盖矩阵

> 队友三份 PRD 的每一条都对应到 V1 的代码 / 测试 / 演示链路。

## 三份 PRD 文档

- **主 PRD**: `Agent-Pilot-产品需求文档.md`（18 节）
- **§17 待确认问题**: `Agent-Pilot-PRD-第17节-待确认问题.md`（6 条）
- **§问题 5 与 6 补充**: `Agent-Pilot-PRD-问题5与6-补充说明.md`

---

## 主 PRD 18 节覆盖

| PRD 节 | 关键内容 | V1 实现位置 | 测试 |
|---|---|---|---|
| §1 定位 | AI 主驾驶、IM 中识别需求 | [`pilot/runtime/intent_router.py`](../pilot/runtime/intent_router.py)（三闸门） | `test_intent_*` |
| §2 设计原则 | 主动但可控 / 双入口 / owner / 多源上下文 / 模块化 | 5 层架构整体体现 | — |
| §3 用户场景 | 5 类典型角色 | `tests/competition/` 用例覆盖 PM / 运营 / 主管 / 学生 / 跨端 | 7 条 e2e |
| §4 整体结构 | 双入口 + 多源 + 模块化执行 | [`pilot/surface/feishu/`](../pilot/surface/feishu/) + [`pilot/surface/dashboard/`](../pilot/surface/dashboard/) | — |
| §5 IM 卡片 | 触发类型 / 卡片结构 / 出现原则 | [`pilot/surface/feishu/cards/builder.py`](../pilot/surface/feishu/cards/builder.py) | `test_task_suggested_card_shape` |
| §6 owner 流转 | 默认 owner / 指派 / 接管 / 阶段 owner | [`pilot/governance/owner_lock.py`](../pilot/governance/owner_lock.py) + [`pilot/runtime/session.py::Task`](../pilot/runtime/session.py) | `test_owner_lock_*` 4 条 |
| §7 上下文包 | 5 类来源 / 确认卡片 / 流程 / 包结构 | [`pilot/context/context_pack.py`](../pilot/context/context_pack.py) | `test_context_pack_*` |
| §8 机器人页 | 任务列表 / 详情 / 日志 / 资产 / 历史 / 设置 | [`pilot/surface/dashboard/`](../pilot/surface/dashboard/) | `test_dashboard_app_has_routes` |
| §9 F-01~F-15 | 15 项基础功能 | 见下表 §9 详表 | 全覆盖 |
| §10 状态机 | 10 状态流转 | [`pilot/runtime/session.py::TaskState`](../pilot/runtime/session.py) | `test_task_state_transition` |
| §11 用户旅程 | 3 条旅程 | `tests/competition/test_judge_e2e.py` | 7 条 e2e |
| §12 页面组件 | 6 类组件 | [`pilot/surface/feishu/cards/`](../pilot/surface/feishu/cards/) + [`pilot/surface/dashboard/static/`](../pilot/surface/dashboard/static/) | — |
| §13 差异化 | 7 项差异化点 | 全部由 5 层 Harness + 三 Agent + MCP 反向暴露实现 | — |
| §14 风险 | 7 项风险 | [`pilot/governance/`](../pilot/governance/)（policy/owner_lock/sandbox/audit） 全对应 | `test_governance.py` |
| §15 MVP | 8 项 P0 + 7 项 P1 | 全部完成（详见 README §快速开始） | — |
| §16 Demo 建议 | 9 步演示链路 | [`docs/DEMO_SCRIPT.md`](DEMO_SCRIPT.md) | — |
| §17 待确认 | 6 个问题 | 见下表 | — |
| §18 一句话总结 | — | [`README.md`](../README.md) 首句 | — |

---

## §9 F-01 ~ F-15 15 项基础功能详表

| 编号 | 功能 | V1 文件 | 测试 |
|---|---|---|---|
| F-01 | IM 文本指令入口 | [`pilot/surface/feishu/router.py`](../pilot/surface/feishu/router.py) | `test_router_*` |
| F-02 | 语音指令入口 | [`pilot/capability/tools/voice.py`](../pilot/capability/tools/voice.py) + [`pilot/surface/feishu/bot.py::_voice_transcribe`](../pilot/surface/feishu/bot.py) | `test_voice_input_flow` |
| F-03 | 主动任务识别 | [`pilot/runtime/intent_router.py::IntentRouter`](../pilot/runtime/intent_router.py) | `test_intent_*` 4 条 |
| F-04 | 任务卡片 | [`pilot/surface/feishu/cards/builder.py::task_suggested_card`](../pilot/surface/feishu/cards/builder.py) | `test_task_suggested_card_shape` |
| F-05 | Planner | [`pilot/runtime/planner.py`](../pilot/runtime/planner.py) + [`pilot/capability/workforce/planner_agent.py`](../pilot/capability/workforce/planner_agent.py) | `test_plan_*` 3 条 |
| F-06 | 上下文确认 | [`pilot/context/context_pack.py`](../pilot/context/context_pack.py) | `test_context_pack_*` |
| F-07 | 资料补充 | [`pilot/surface/feishu/cards/builder.py::context_confirm_card`](../pilot/surface/feishu/cards/builder.py) | `test_context_confirm_card` |
| F-08 | 文档生成 | [`pilot/capability/tools/doc.py`](../pilot/capability/tools/doc.py) + [`pilot/capability/skills/pilot-doc/SKILL.md`](../pilot/capability/skills/pilot-doc/SKILL.md) | `test_short_doc` |
| F-09 | PPT/画布生成 | [`pilot/capability/tools/slide.py`](../pilot/capability/tools/slide.py) + [`pilot/capability/tools/canvas.py`](../pilot/capability/tools/canvas.py) | `test_three_in_one` |
| F-10 | 执行人指派 | [`pilot/governance/owner_lock.py`](../pilot/governance/owner_lock.py) | `test_owner_lock_transfer` |
| F-11 | 状态锁定与同步 | F-10 + [`pilot/surface/sync/hub.py`](../pilot/surface/sync/hub.py) | `test_owner_lock_basic` + `test_hub_*` |
| F-12 | 机器人任务中心 | [`pilot/surface/dashboard/`](../pilot/surface/dashboard/) | `test_dashboard_app_has_routes` |
| F-13 | 导出与分享 | [`pilot/capability/tools/archive.py`](../pilot/capability/tools/archive.py) | `test_archive_bundle` |
| F-14 | 演练与修改 | [`pilot/capability/tools/slide.py::slide_rehearse`](../pilot/capability/tools/slide.py) | 集成于 `test_three_in_one` |
| F-15 | 冲突解决 | [`pilot/surface/sync/hub.py::reconcile`](../pilot/surface/sync/hub.py) (CRDT 自然支持) | `test_hub_history_replay_to_late_joiner` |

---

## §17 第 17 节 6 个待确认问题（V1 全部回答）

| # | 问题 | V1 结论 | 实现位置 |
|---|---|---|---|
| 1 | IM 卡片基于飞书还是自研 | **飞书开放平台**（lark-oapi WS + CardKit 2.0） | `pilot/surface/feishu/client.py` |
| 2 | PPT vs 自由画布 | **双形态**：python-pptx + tldraw + Mermaid | `pilot/capability/tools/slide.py` + `pilot/capability/tools/canvas.py` |
| 3 | 多端 | **iOS + macOS（Flutter 三合一含 Android+Web）** | `flutter_client/` |
| 4 | 资料读取 | **真 API**（lark-oapi）+ 多维表格 + 上传/链接补充 | `pilot/capability/tools/doc.py` |
| 5 | 主动识别阈值 | **规则 + LLM 混合**（PRD 补充说明 §问题 5） | `pilot/runtime/intent_router.py::detect` |
| 6 | owner 与群角色 | **轻量指派**（PRD 补充说明 §问题 6） | `pilot/governance/owner_lock.py` |

---

## §问题 5 与 6 补充说明（落地点）

### 问题 5 三闸门

`pilot/runtime/intent_router.py` 内置：
- **闸门 1 规则层**：`EXPLICIT_KEYWORDS` 关键词命中 + `TASK_SEMANTIC_PATTERNS` 任务语义命中 + 上下文条件
- **闸门 2 LLM 层**：可注入 `LLMJudgeFn`，输出 `LLMJudgement`（is_task / task_type / goal / resources / next_step）
- **闸门 3 最小信息**：goal + form + audience 三选二即 READY，不足则 NEEDS_CLARIFY

### 问题 6 轻量指派

`pilot/governance/owner_lock.py`：
- 默认 owner = 触发者
- 三按钮：`pilot.task.confirm` / `pilot.task.assign` / `pilot.task.claim`
- `lock_for_execution` 进入执行后锁定，其他成员不能重复触发
- `request_claim` + `transfer` 实现"我来执行 → 当前 owner 同意"流程

---

## 四个加分项（PRD §G1-G4）

| 加分项 | V1 实现 | 测试 |
|---|---|---|
| **G1 离线支持** | CRDT 天然支持 + `SyncHub.reconcile` | `test_hub_history_replay_to_late_joiner` |
| **G2 高级 Agent 能力** | `mentor.clarify` + `mentor.summarize` + Workforce 三 Agent harness | `test_clarifier_*` + `test_workforce_three_agent_e2e` |
| **G3 富媒体** | doc.append 支持图片/表格/Mermaid；canvas 支持 frame/箭头；PPT 5 模板 | 集成于 `test_three_in_one` |
| **G4 第三方平台集成** | lark-oapi 直连 + lark-cli 29 SKILL submodule + lark-mcp 反向暴露 | `test_mcp_server_creates_app` |

---

## 验收硬指标（V1 完成 = 全部 ✅）

- [x] 飞书发"产品方案 + 架构图 + 评审 PPT 三件套" **30 秒内**完成（mocked，真 LLM 约 90 秒）
- [x] 飞书发"帮我做个汇报"弹出橙色澄清卡，4 个按钮**任意一个**都能继续推进（修复 v13 P0）
- [x] 三端可同时打开（手机飞书 + Web Dashboard + Flutter macOS），`test_multi_end_event_consistency` 守护
- [x] 75/75 单元 + e2e 测试全绿
- [x] pptx 文件可下载用 Keynote 打开有 6+ 页（`_write_pptx` 5 模板）
- [x] 服务器 `systemctl status` 无 v13/v12/v4/v3 任何残留
- [x] GitHub `v1-rewrite` 分支只有 V1 代码
- [x] MCP server 可被 Cursor/Claude/Trae 反向调用
- [x] PRD §9 F-01 ~ F-15 全部 15 项基础功能在 V1 中可演示
- [x] PRD §10 任务状态机 10 状态全部可触发
- [x] AGENTS.md cascade 在 Cursor / Claude Code 里能被正确加载
