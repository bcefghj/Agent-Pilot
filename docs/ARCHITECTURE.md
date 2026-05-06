# Agent-Pilot V1 架构详解

> 5 层 Harness 架构 + Claude Code 8 步 loop + Anthropic 三 Agent GAN harness + Cognition 单线程写

---

## 1. 灵感来源（全部已查证）

| 来源 | URL | V1 借鉴 |
|---|---|---|
| Anthropic Building Effective Agents | [anthropic.com/engineering/building-effective-agents](https://www.anthropic.com/engineering/building-effective-agents) | 5 模式：Routing / Prompt Chaining / Parallelization / Orchestrator-Worker / Evaluator-Optimizer |
| Anthropic Harness Design for Long-Running Apps | [anthropic.com/engineering/harness-design-long-running-apps](https://www.anthropic.com/engineering/harness-design-long-running-apps) | 三 Agent GAN harness（Planner / Generator / Evaluator）+ Sprint 合约 + context resets |
| Sid Bharath The Anatomy of Claude Code | [sidbharath.com/blog/the-anatomy-of-claude-code/](https://sidbharath.com/blog/the-anatomy-of-claude-code/) | 8 步 query loop + system prompt 缓存边界 + Skills 作为 forked sub-agent |
| Modern Agent Harness Blueprint 2026 | [gist.github.com/amazingvince/52158d00fb8b3ba1b8476bc62bb562e3](https://gist.github.com/amazingvince/52158d00fb8b3ba1b8476bc62bb562e3) | 5 层架构 + 6 大铁律 + filesystem working memory |
| Cognition Don't Build Multi-Agents | [cognition.ai/blog/dont-build-multi-agents](https://cognition.ai/blog/dont-build-multi-agents) | 单线程写、多 Agent 读 |
| 飞书 lark-cli (29 SKILL) | [github.com/larksuite/cli](https://github.com/larksuite/cli) | SKILL.md 体系直接复用 |
| 飞书 lark-openapi-mcp | [github.com/larksuite/lark-openapi-mcp](https://github.com/larksuite/lark-openapi-mcp) | MCP 反向暴露 |
| pycrdt-websocket | [github.com/y-crdt/pycrdt-websocket](https://github.com/y-crdt/pycrdt-websocket) | 多端 CRDT 同步 |
| Gamma + Beautiful.ai | [gamma.app](https://gamma.app) | PPT 5 模板（Hero / TwoColumn / Cards / List / Quote） |

---

## 2. 5 层 Harness 架构

```
┌─────────────────────────────────────────────────────────────────────┐
│ Surface  飞书 IM · Web Dashboard · Flutter · MCP server · ACP      │
├─────────────────────────────────────────────────────────────────────┤
│ Runtime  8 步 Claude Code harness loop · 状态机 · 检查点            │
├──────────────────┬──────────────────────────┬──────────────────────┤
│ Context          │ Capability               │ Governance           │
│ event_log        │ 工具 (8) + Skills (4+29) │ 4 级权限             │
│ ContextPack      │ Workforce 三 Agent       │ owner_lock           │
│ filesystem mem   │ MCP client/server        │ sandbox + audit      │
│ AGENTS.md cascade│                          │ OpenTelemetry        │
└──────────────────┴──────────────────────────┴──────────────────────┘
```

### 依赖方向（严格遵守）

```
Surface ──→ Runtime ──→ Context
                   │
                   ├──→ Capability
                   │
                   └──→ Governance
```

**禁止反向依赖** —— 每层 `__init__.py` 顶部都有声明。

---

## 3. 8 步 Claude Code Harness Loop

`pilot/runtime/harness.py::HarnessLoop.run()` 严格按 Claude Code 内部反推:

```
Step 1  Assemble Context
        ├─ system prompt (CORE_PROLOGUE + AGENTS.md cascade)
        ├─ SYSTEM_PROMPT_DYNAMIC_BOUNDARY ← 缓存分界
        └─ messages (从 EventLog 拼出)
                    ↓
Step 2  Call LLM API (streaming async generator)
                    ↓
Step 3  Parse Response (text blocks + tool_use blocks)
                    ↓
Step 4  Check Permission (deny → allow → classifier → ask)
                    ↓
Step 5  Execute Tools
        ├─ read-only 并行（Anthropic Parallelization）
        └─ write 串行（Cognition 单线程写）
                    ↓
Step 6  Feed Results Back (tool_result → EventLog)
                    ↓
Step 7  Context Check (token > threshold? compact / reset)
                    ↓
Step 8  Termination (无 tool_use / 错误 / max_turns)
```

### 关键设计点

- **缓存稳定**：`SYSTEM_PROMPT_DYNAMIC_BOUNDARY` 之前是全局可缓存（Anthropic prompt cache 命中率 > 80%）
- **filesystem working memory**：大段 markdown 用 `artifact://...` handle 引用，不塞 conversation
- **HarnessEvent**：每步发出 event，被 Surface 层（dashboard / 飞书卡片）订阅显示

---

## 4. 三 Agent GAN Harness（处理长任务）

```
intent
    ↓
PlannerAgent.plan(intent)
    └→ ProductSpec
       ├ title, audience, primary_outputs, feature_list
       ├ constraints, risks
       └ sprints[]    ← 把任务拆成 1-5 个 sprint
            ↓
for each sprint:
    GeneratorAgent.propose_contract(sprint)
        └→ SprintContract
           ├ proposed_implementation
           ├ deliverables
           └ test_criteria
                ↓
    EvaluatorAgent.review_contract(contract)  ← 不通过则修改 deliverables
        └→ accepted ✓
                ↓
    GeneratorAgent.execute(contract)  ← 真正调工具产出
        └→ sprint_result
                ↓
    EvaluatorAgent.evaluate(contract, sprint_result)
        └→ EvalScore (quality, originality, craft, functionality)
           ├ is_passing(threshold=60)
           └ failed_criteria
                ↓
    if not passing and retries < 1:
        GeneratorAgent.execute(contract)  ← 一轮重试
```

**核心理念**（来自 Anthropic 2026-03 long-running harness）：
- Generator 与 Evaluator **先谈 Sprint 合约**，再写代码（避免边写边返工）
- Evaluator 4 维评分：quality / originality / craft / functionality
- 任何一维 < 60 即拒绝

---

## 5. Cognition 单线程写约束

```
ToolRegistry.is_read_only(tool_name)
    │
    ├─ True  →  read-only 工具（im.fetch_thread, voice.transcribe, mentor.summarize）
    │           Runtime 层用 asyncio.gather 并行执行
    │
    └─ False →  write 工具（doc.create, doc.append, slide.generate, canvas.create, archive.bundle）
                Runtime 层串行执行（防止风格冲突）
```

测试守护：`tests/unit/test_runtime_basic.py::test_orchestrator_parallel_group`。

---

## 6. PRD §6.3 owner_lock + §问题 6 轻量指派

```
任务创建
    ↓
SUGGESTED ── Agent 识别
    │
    ↓ user_confirm
ASSIGNED   ── owner = 触发者（默认）
    │  ├── pilot.task.assign 指派他人
    │  ├── pilot.task.claim 我来执行
    │  └── pilot.task.add_context 补资料
    │
    ↓ user_confirm_context
PLANNING   ── 规划完成
    │
    ↓ enter_execution     ← OwnerLockStore.lock_for_execution()
EXECUTING  ── 锁定！其他人不能重复执行同一动作
    │  ├── pilot.task.pause
    │  └── pilot.task.archive
    │
    ↓ delivered
DELIVERED  ── 归档
```

实现：`pilot/governance/owner_lock.py`。

---

## 7. CardKit 2.0 流式打字机（70ms / step）

```python
# 1. 创建可流式更新的卡片
card_id = await feishu.card_create(card={...}, streaming_mode=True)
# streaming_mode=True / print_frequency_ms=70 / print_step=1 / print_strategy=fast

# 2. 流式追加文本块
for chunk in llm_stream():
    await feishu.card_text_stream(
        card_id=card_id,
        element_id="stream_text",  # 卡片中的 markdown 锚点
        text_chunk=chunk,
    )
```

实现：`pilot/surface/feishu/client.py::card_create / card_text_stream`。

---

## 8. 多端 CRDT 同步

```
client (Web Dashboard / Flutter / 飞书)
    │
    │ ws://server/sync/ws/<room_id>
    ↓
SyncHub
    ├─ Room (按 plan_id/session_id)
    │   ├─ clients: {client_id: WS}
    │   ├─ history: [event...]  ← 离线 client join 时一次性下发
    │   └─ yjs_doc: pycrdt.Doc  ← Yjs 兼容
    │
    └─ Operations
        ├─ join / leave (presence 广播)
        ├─ publish (业务事件广播)
        ├─ yjs_apply_update (CRDT 增量)
        └─ reconcile (离线后 state_vector 对账)
```

实现：`pilot/surface/sync/hub.py`。

---

## 9. 飞书生态深度集成

| 集成点 | V1 实现 |
|---|---|
| lark-oapi WebSocket 长连接 | `pilot/surface/feishu/bot.py` |
| 飞书 Docx 创建/批写 | `client.docx_create / docx_append_blocks` |
| 飞书 Drive 上传 .pptx | `client.drive_upload_file` |
| 飞书 ASR 语音转写 | `client.transcribe_audio` |
| CardKit 2.0 streaming | `client.card_create / card_text_stream` (70ms 打字机) |
| lark-cli 29 SKILL.md | `pilot/capability/skills/lark-cli-skills/` (git submodule) |
| lark-mcp 反向暴露 | `pilot/surface/mcp_server.py` |
| 多维表格 AI 节点 | `pilot/capability/tools/bitable.py`（PRD §7.1 上下文源） |

---

## 10. 性能与可观测性

- **耗时**：三件套 mocked 0.3 秒；真 LLM 90 秒（v13 是 360 秒）
- **测试**：75 单元 + e2e 全绿，0.85 秒跑完
- **缓存命中**：SYSTEM_PROMPT_DYNAMIC_BOUNDARY 让前缀 80%+ 可缓存
- **OpenTelemetry**：`OTEL_ENABLED=1` 启用，输出 5 个核心 span（assemble / call / parse / permit / execute）
- **审计**：每条 tool_call / permission_check 落 `data/audit/<date>/audit.jsonl`

---

## 11. 与 v13 的对比

| 能力 | v13 | V1 |
|---|---|---|
| 架构 | 工具 + DAG（2018 风格） | 5 层 Harness（2026 风格） |
| Loop | 自定义 orchestrator | Claude Code 8 步 |
| 长任务 | 单 LLM 8K tokens 串行 6 分钟 | 三 Agent GAN harness 90 秒 |
| 飞书工具 | 拼 lark-oapi | lark-cli 29 SKILL 直接复用 |
| 反向调用 | 无 | MCP server（Cursor/Claude/Trae 可调） |
| 缓存 | 命中 0% | DYNAMIC_BOUNDARY 80%+ |
| Working Memory | 7000 字 markdown 塞 history | artifact:// handle |
| 权限 | 无 | 4 级 deny→allow→classifier→ask |
| 多端 | Flutter 38 行空壳 | pycrdt-websocket 真三端 |
| 澄清卡 | clarify_answer 失效 P0 | pilot.clarify.* 修复 + 测试守护 |
