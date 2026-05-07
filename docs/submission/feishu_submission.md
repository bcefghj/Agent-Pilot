# Agent-Pilot · 飞书 AI 校园挑战赛 复赛提交文档

> 赛道：基于 IM 的办公协同智能助手（公开版）
> 命题：Agent-Pilot · 从 IM 对话到演示稿的一键智能闭环
> 提交日期：2026 年 5 月 7 日

---

## 一、个人信息

### 小组参赛

| 姓名 | 角色 | 项目中负责的工作简述 | 个人基本信息 |
|------|------|---------------------|-------------|
| 李洁盈 | 组长 | 产品设计、UI/UX 交互设计、用户体验优化、内容运营策略、竞品调研分析 | 学校/专业详见下方 |
| 戴尚好 | 成员 | Multi-Agent Pipeline 架构设计与全栈实现、MiniMax LLM 集成、飞书 Bot 开发、服务器部署运维、CI/CD 流程搭建 | 学校/专业详见下方 |

#### 李洁盈

- **角色**：产品 / 设计
- **Email**：JieyingLiii@outlook.com
- **GitHub**：github.com/Jane-0213
- **小红书**：李什么盈
- **个人主页**：janeliii.netlify.app
- **负责工作**：
  - 产品需求分析与 PRD 撰写
  - 飞书 Bot 交互流程设计（对话 UX、卡片 UI）
  - Dashboard 界面设计（三段式布局、配色方案）
  - 竞品调研（Coze / Dify / 传统飞书 Bot 对比）
  - 产品宣传网页设计与文案
  - 演示视频脚本策划

#### 戴尚好

- **角色**：全栈 / Agent / 部署
- **Email**：bcefghj@163.com
- **GitHub**：github.com/bcefghj
- **小红书**：bcefghj
- **个人主页**：bcefghj.github.io
- **负责工作**：
  - Multi-Agent Pipeline 核心架构设计与实现（6 Agent 协作流水线）
  - MiniMax M2.7 LLM 集成（tool calling、联网搜索、prompt 工程）
  - 飞书 Bot 开发（lark-oapi WebSocket、CardKit 交互卡片）
  - Dashboard 后端（FastAPI + SSE 实时推送）
  - 反向 MCP Server（供 Cursor/Claude Desktop 接入）
  - 多端协同框架（Flutter 移动端 + Web Dashboard）
  - 服务器部署（Ubuntu 22.04 + systemd + nginx + UFW）
  - 测试体系（单元测试 + 竞赛 e2e 真实 API 测试）
  - CI/CD 流程（GitHub Actions）

---

## 二、项目结果展示

### 1）Demo 展示

#### 在线体验入口

| 入口 | URL | 说明 |
|------|-----|------|
| **产品介绍网页** | http://8.136.98.175 | 产品全景介绍 + 动画演示 |
| **Live Demo** | http://8.136.98.175/demo | 在线体验 Agent-Pilot 对话（Web Chat） |
| **Dashboard** | http://8.136.98.175/dashboard | 实时 Agent 协作过程可视化 |
| **MCP Server** | http://8.136.98.175/sse | 供 Cursor/Claude Desktop 接入的反向 MCP |
| **技术白皮书 PDF** | http://8.136.98.175/agent_pilot_report.pdf | 50 页 A4 技术文档 |
| **GitHub 仓库** | https://github.com/bcefghj/Agent-Pilot | 完整源码（185 文件，MIT 开源） |

#### 核心演示场景

**场景 1：从 IM 对话到文档的一键闭环**

用户在飞书 IM 中发送：「帮我写一份 AI Agent 多端协同方案」

Agent-Pilot 自动执行：
1. IntentAgent 识别意图 → task_type = "doc"
2. PlannerAgent 生成 7 章结构化大纲
3. ResearchAgent 通过 MiniMax tool calling 联网搜索最新资料
4. WriterAgent 按章节撰写，融合搜索数据（5000+ 字）
5. ReviewAgent 5 维度自评 → 不通过则反馈给 Writer 重写（最多 3 轮）
6. BuilderAgent 将内容写入飞书文档，返回链接

全程耗时约 90 秒，用户在飞书内即可看到完整文档。

**场景 2：从 IM 对话到 PPT 的一键闭环**

用户发送：「做一份 8 页关于飞书开放平台集成的 PPT」

Agent-Pilot 自动执行 ppt_pipeline：大纲 → 联网搜索 → 撰写 → 审核 → python-pptx 生成 .pptx 文件。

**场景 3：三件套（文档 + PPT + 归档）**

用户发送：「AI Agent 办公自动化三件套」

Agent-Pilot 执行 trio_pipeline，一次请求同时产出文档、PPT 和归档文件。

**场景 4：多端协同**

- 飞书 IM（移动端/桌面端）触发任务
- Dashboard（Web）实时展示 Agent 协作过程
- Flutter 移动端查看任务进度与结果
- 任一端操作，其他端实时同步

---

### 2）核心代码展示

#### 2.1 Multi-Agent Pipeline 架构（核心编排）

```python
# pilot/agents/pipeline.py — 文档生成流水线
async def doc_pipeline(state: AgentState) -> AgentState:
    """文档生成流水线: Planner → Research → Writer ⇄ Review → Builder"""
    event_log = _get_event_log(state)
    start_time = time.time()

    # Phase 1: 规划
    await _emit(event_log, "agent.start", {"agent": "PlannerAgent"})
    planner = PlannerAgent()
    state = await planner.safe_execute(state)

    # Phase 2: 联网搜索
    await _emit(event_log, "agent.start", {"agent": "ResearchAgent"})
    researcher = ResearchAgent()
    state = await researcher.safe_execute(state)

    # Phase 3: 撰写 + 审核循环（最多 3 轮）
    writer = WriterAgent()
    reviewer = ReviewAgent()
    for i in range(MAX_REVIEW_ITERATIONS):
        state = await writer.safe_execute(state)
        state = await reviewer.safe_execute(state)
        if state.get("review_pass"):
            break
        # 不通过 → feedback 注入 → 重写
        state["intent"] += f"\n[Review Feedback]: {state['review_feedback']}"

    # Phase 4: 构建交付
    builder = BuilderAgent()
    state = await builder.safe_execute(state)

    # Phase 5: 生成任务总结
    state["summary"] = await _generate_summary(state)
    return state
```

#### 2.2 BaseAgent 抽象类 + 错误恢复（参考 Claude Code）

```python
# pilot/agents/base.py
class BaseAgent(ABC):
    """所有 Agent 的基类，内置步骤预算 + 错误恢复 + 上下文压缩。"""

    MAX_STEP_BUDGET = 30  # 防止无限循环

    async def safe_execute(self, state: AgentState) -> AgentState:
        """带保护的执行入口 — 步骤预算 + 重试 + 上下文压缩。"""
        self._step_count += 1
        if self._step_count > self.MAX_STEP_BUDGET:
            raise StopIteration(StopReason.MAX_STEPS)
        try:
            return await ErrorRecovery.retry_with_backoff(
                lambda: self.execute(state), max_retries=3
            )
        except ContextOverflowError:
            state = self._compress_context(state)
            return await self.execute(state)
```

#### 2.3 MiniMax Tool Calling 联网搜索

```python
# pilot/agents/researcher.py — ResearchAgent
class ResearchAgent(BaseAgent):
    """利用 MiniMax M2.7 的 function calling 能力自主搜索。"""

    _RESEARCH_SYSTEM_PROMPT = """你是专业研究员。
    限制：只接受 2024-2026 年的数据。
    你必须使用 web_search 工具获取实时信息。
    输出格式: {"data": "研究发现...", "source": "来源URL"}"""

    async def execute(self, state: AgentState) -> AgentState:
        # MiniMax 模型自主决定搜什么 → tool_call → 执行搜索 → 整理结果
        results = await self._call_llm(
            system=self._RESEARCH_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"研究大纲: {state['outline']}"}],
            tools=[{"name": "web_search", "description": "联网搜索"}]
        )
        state["research_results"] = results
        return state
```

#### 2.4 Circuit Breaker（熔断器保护）

```python
# pilot/llm/client.py
class CircuitBreaker:
    """LLM API 熔断器: CLOSED → OPEN → HALF_OPEN 状态机。
    5 次连续失败 → 熔断 5 分钟 → 半开状态试探恢复。"""

    FAILURE_THRESHOLD = 5
    RECOVERY_TIMEOUT = 300  # 5 minutes

    def allow_request(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if time.time() - self.last_failure > self.RECOVERY_TIMEOUT:
                self.state = "half_open"
                return True
            return False
        return True  # half_open: 允许一次试探
```

#### 2.5 飞书交互卡片

```python
# pilot/surface/feishu/cards/builder.py
def task_delivered_card(task_id, title, artifacts, summary, elapsed_sec, iterations):
    """任务完成交付卡片 — 绿色标题 + 摘要 + 耗时 + 产物链接 + 操作按钮。"""
    return {
        "header": {"title": {"tag": "plain_text", "content": f"🛬 任务完成"},
                   "template": "green"},
        "elements": [
            {"tag": "markdown", "content": f"**{title}**\n\n{summary}"},
            {"tag": "markdown", "content": f"⏱ 耗时 {elapsed_sec}s · 迭代 {iterations} 轮"},
            # 产物链接列表...
            {"tag": "action", "actions": [/* 重新生成 / 归档 / 查看详情 */]}
        ]
    }
```

---

### 3）项目亮点介绍

#### 维度 1：完整性与价值（50%）

**解决什么问题 / 痛点？**

在快节奏的团队协作中，从一次 IM 对话到最终的演示文稿，需要经历：
- 意图理解 → 信息搜集 → 文档撰写 → 多方讨论 → PPT 制作 → 汇报归档

这个过程涉及 4+ 个应用之间的反复切换，大量重复操作消耗创造力。

Agent-Pilot 将整个流程压缩为**一句话触发**：用户在飞书 IM 中说一句自然语言，AI Agent 自动完成全链路。

**AI 在其中起到什么关键作用？**

AI 不是"功能增强"，而是**主驾驶（Pilot）**：
- 6 个专业 AI Agent 各司其职，形成完整的认知-执行闭环
- LLM 不仅生成内容，更**自主决策**（搜什么、写多少、质量够不够）
- Human-in-the-Loop 仅在关键节点（大纲确认）介入

**流程是否完整闭环？能否落地使用？**

完整闭环验证：

| 输入 | 经过 | 输出 | 状态 |
|------|------|------|------|
| "帮我写一份 AI 报告" | Intent→Planner→Research→Writer→Review→Builder | 飞书文档链接 | 已验证 |
| "做 8 页 PPT" | Intent→Planner→Research→Writer→Review→Builder | .pptx 文件 | 已验证 |
| "三件套" | trio_pipeline | 文档+PPT+归档 | 已验证 |
| "你好" | IntentAgent→chat_reply_card | 友好回复+引导 | 已验证 |
| "帮我做个汇报"（模糊） | IntentAgent→clarify | 主动澄清卡片 | 已验证 |

通过 14/14 PRD 场景测试（真实 MiniMax API 调用）。

**Demo 是否稳定、可正常演示？**

- 服务器 7×24 运行（Ubuntu 22.04, systemd 管理）
- Circuit Breaker 熔断保护 → API 故障时优雅降级
- 指数退避重试 → 瞬时错误自动恢复
- 步骤预算（MAX_STEP_BUDGET=30）→ 防止 Agent 死循环
- Dashboard 实时监控 Agent 状态

**带来什么实际价值 / 效率提升？**

| 传统方式 | Agent-Pilot | 提升 |
|----------|-------------|------|
| 写一份研究报告：搜索+整理+撰写 2-4 小时 | 90 秒自动完成 | 96%+ 时间节省 |
| 做 8 页 PPT：大纲+内容+排版 3-5 小时 | 120 秒自动生成 | 97%+ 时间节省 |
| 多端状态同步：手动复制粘贴 | 实时自动同步 | 100% 消除人工 |

#### 维度 2：创新性（25%）

**AI 相关创新点**

1. **Multi-Agent Pipeline（6 Agent 专业分工）**
   - 参考 CrewAI 角色分工 + LangGraph TypedDict 共享状态
   - 非传统单 Agent 架构，而是分工明确的专家团队
   - 每个 Agent 有独立的 system prompt、工具集、验证标准

2. **MiniMax M2.7 Tool Calling 联网搜索**
   - 不是硬编码搜索关键词，而是**模型自主决策**搜什么
   - 结合时间约束（2024-2026 年数据）+ few-shot 示例提升搜索质量
   - 搜索质量随 LLM 能力提升自动改善

3. **ReviewAgent 自评迭代（参考 DeepPresenter 论文）**
   - 5 维度自评：数据支撑 / 结构完整 / 引用来源 / 内容密度 / 字数达标
   - 最多 3 轮迭代，feedback 注入让 Writer 针对性修改
   - 实现"生成-评审-改进"闭环，内容质量有保障

4. **Human-in-the-Loop 大纲确认（参考 GenSlide AAAI 2025）**
   - 关键决策节点由人把关
   - 飞书 CardKit 交互卡片实现 Approve/Revise
   - 平衡自动化效率与人类控制力

5. **Claude Code 架构的错误恢复**
   - 步骤预算防无限循环
   - 上下文压缩防溢出
   - Circuit Breaker 防级联故障
   - 指数退避重试防瞬时错误

**方案差异化亮点**

| 对比项 | Coze / Dify 等平台 | 传统飞书 Bot | Agent-Pilot |
|--------|-------------------|-------------|-------------|
| Agent 架构 | 单 Agent + 工具调用 | 无 Agent | 6 Agent Pipeline |
| 内容质量保障 | 无 | 无 | ReviewAgent 自评迭代 |
| 联网搜索 | 固定插件 | 无 | LLM 自主决策搜索 |
| 人机协同 | 全自动 | 全手动 | Human-in-the-Loop |
| 跨端同步 | 无 | 无 | SSE + WebSocket 实时同步 |
| 可观测性 | 日志 | 无 | Dashboard 实时 Agent 可视化 |

**是否可复用、可推广**

- 架构模式通用：Pipeline 可扩展新 Agent（如 TranslateAgent、DesignAgent）
- 平台无关：LLM 接口可切换（MiniMax / GPT / Claude）
- IM 无关：Surface 层抽象，可扩展到 Slack、钉钉、微信
- 开源可复制：MIT License，185 文件完整工程

#### 维度 3：技术实现性（25%）

**AI 技术使用深度**

| 技术点 | 深度说明 |
|--------|----------|
| Prompt Engineering | 每个 Agent 独立 system prompt，含角色定义、输出格式约束、few-shot 示例 |
| Tool Calling | MiniMax M2.7 原生 function calling，非规则触发 |
| 多轮迭代 | Writer ⇄ Reviewer 闭环，feedback 注入机制 |
| Context Management | AgentState TypedDict 共享 + 上下文压缩策略 |
| Error Handling | Circuit Breaker + 指数退避 + 步骤预算 + 降级策略 |

**技术架构 / 方案合理性**

```
┌────────────────────────────────────────────────────────────┐
│                    Surface Layer                            │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │飞书 Bot  │  │ Dashboard    │  │ MCP Server         │   │
│  │(lark-oapi│  │ (FastAPI+SSE)│  │ (反向工具暴露)      │   │
│  │ WebSocket)│  └──────────────┘  └────────────────────┘   │
│  └──────────┘                                              │
├────────────────────────────────────────────────────────────┤
│                    Agent Layer                              │
│  Intent → Planner → Research → Writer ⇄ Review → Builder  │
│  (共享 AgentState TypedDict，Pipeline 编排)                  │
├────────────────────────────────────────────────────────────┤
│                    Capability Layer                         │
│  doc_tool · slide_tool · canvas_tool · web_search          │
│  lark_tools (Doc API / Drive API)                          │
├────────────────────────────────────────────────────────────┤
│                    Infrastructure                           │
│  MiniMax M2.7 Client · Circuit Breaker · EventLog          │
│  Session State Machine (10 states) · Filesystem Memory     │
└────────────────────────────────────────────────────────────┘
```

**工程规范、稳定性、可扩展性**

- **代码规模**：185 个源文件，Python 90.5% + HTML 5.4% + Dart 3.2%
- **测试覆盖**：16 个单元测试文件 + 竞赛 e2e 测试（真实 API）
- **CI/CD**：GitHub Actions 自动化（lint + test + deploy）
- **部署**：systemd 进程管理 + nginx 反代 + UFW 防火墙
- **监控**：EventLog + Dashboard SSE 实时观测
- **安全**：owner_lock 防多人冲突 + policy 权限控制 + sandbox 沙箱

---

### 4）AI 亮点介绍

#### 项目中使用了哪些高阶 AI 技巧？

1. **Multi-Agent 协作编排**
   - 不是简单的"一个 LLM 回答问题"，而是 6 个专业 Agent 分工协作
   - 参考 LangGraph、CrewAI、AutoGen 等前沿框架的设计理念
   - 每个 Agent 有独立的认知边界和验证标准

2. **LLM 自主工具调用（Tool Calling）**
   - ResearchAgent 不硬编码搜索关键词，让 MiniMax M2.7 自主决定搜什么
   - 模型判断需要哪些信息 → 发出 web_search tool_call → 获取结果 → 整理
   - 搜索行为随 LLM 能力进化而自动提升

3. **生成-评审-迭代循环（Generate-Review-Refine）**
   - 参考 DeepPresenter 论文的 generate-then-review 范式
   - ReviewAgent 从 5 个维度量化评估生成质量
   - 不通过时精确反馈（哪里不好、怎么改），Writer 针对性修改

4. **Prompt 工程最佳实践**
   - 角色定义 + 输出格式约束 + few-shot 示例 + 时间约束
   - `_strip_thinking` 清理 MiniMax 内部标记（`<think>` 和 `[TOOL_CALL]`）
   - 结构化 JSON 输出（response_format: json_object）

5. **错误恢复与降级策略**
   - Claude Code 风格的步骤预算（防 Agent 死循环）
   - Circuit Breaker 模式（API 连续失败时熔断保护）
   - 上下文溢出时自动压缩（截断历史、摘要化）

#### 项目中人和 AI 的分工是怎么样的？

| 环节 | AI 做什么 | 人做什么 |
|------|-----------|----------|
| 意图理解 | IntentAgent 自动分类（doc/ppt/trio/chat/clarify） | — |
| 大纲规划 | PlannerAgent 生成结构化大纲 | 用户确认/修改大纲（CardKit 交互） |
| 信息搜集 | ResearchAgent 自主联网搜索 | — |
| 内容撰写 | WriterAgent 按章节生成 | — |
| 质量审核 | ReviewAgent 5 维度自评 | — |
| 产物交付 | BuilderAgent 写入飞书/生成 PPT | 用户查看、精细调整 |

核心理念：**AI 是主驾驶（Pilot），人是副驾驶（Co-pilot）**。AI 处理 90% 的重复工作，人只在关键决策点介入。

#### 项目中包含了哪些核心模型选型思路？

| 选型维度 | 决策 | 理由 |
|----------|------|------|
| 基础模型 | MiniMax-M2.7-highspeed | 比赛指定平台；支持 tool calling；速度快（highspeed 版本） |
| 搜索策略 | MiniMax 原生联网搜索 | 无需第三方 API；模型自主决策搜索意图；数据时效性好 |
| 多 Agent 框架 | 自研 Pipeline（参考 CrewAI/LangGraph） | 轻量无依赖；完全可控；适配比赛场景 |
| 文档生成 | 飞书 Doc API | 飞书原生体验；无需跳出 IM；支持富文本 |
| PPT 生成 | python-pptx | 纯 Python 实现；模板可控；无外部依赖 |

#### 引入 AI 后对原有工作流带来了哪些改变？

**Before（传统工作流）**：
```
IM 讨论 → 手动搜索资料 → 打开文档编辑器 → 逐段撰写
→ 同事审核 → 修改 → 打开 PPT 软件 → 制作幻灯片
→ 导出 → 分享链接 → 归档
```
**耗时**：4-8 小时 | **需要切换**：5+ 个应用 | **认知负担**：高

**After（Agent-Pilot）**：
```
IM 中说一句话 → Agent 全自动执行 → 飞书内查看结果
```
**耗时**：90-120 秒 | **需要切换**：0 个应用 | **认知负担**：极低

---

### 5）其他信息补充

#### 竞品分析深度对比

| 维度 | Coze (字节) | Dify | 传统飞书 Bot | **Agent-Pilot** |
|------|-------------|------|-------------|-----------------|
| Agent 模式 | 单 Agent + Plugin | DAG 工作流 | 规则触发 | **6 Agent Pipeline** |
| 联网搜索 | 插件调用 | 工具节点 | 无 | **LLM 自主 tool calling** |
| 质量保障 | 无 | 无 | 无 | **ReviewAgent 自评迭代** |
| 人机协同 | 全自动 | 节点确认 | 全手动 | **CardKit 大纲确认** |
| 多端同步 | 无 | 无 | 无 | **SSE + WebSocket** |
| 实时可观测 | 日志 | 节点状态 | 无 | **Dashboard Agent 可视化** |
| 错误恢复 | 简单重试 | 节点重试 | 无 | **Circuit Breaker + 步骤预算** |

#### 学术参考

| 论文/项目 | 年份 | 我们借鉴了什么 |
|-----------|------|---------------|
| GenSlide (AAAI 2025) | 2025 | Human-in-the-Loop：Approve/Revise 大纲确认 |
| DeepPresenter | 2024 | Generate-then-Review：自评迭代提升质量 |
| CrewAI | 2024 | Agent 角色分工 + Pipeline 编排模式 |
| LangGraph | 2024 | TypedDict 共享状态 + 流式编排 |
| Claude Code (Anthropic) | 2026 | 错误恢复决策树 + 步骤预算 + 上下文压缩 |

#### 技术栈全景

| 层级 | 技术选择 |
|------|----------|
| LLM | MiniMax-M2.7-highspeed（tool calling + 联网搜索） |
| Agent 框架 | 自研 Multi-Agent Pipeline（参考 CrewAI/LangGraph） |
| 后端 | Python 3.10+ / FastAPI / asyncio |
| 飞书集成 | lark-oapi（WebSocket Bot + Doc API + Drive API） |
| 前端 | HTML/CSS/JS（Dashboard）+ Flutter（移动端） |
| 部署 | Ubuntu 22.04 / systemd / nginx / UFW |
| CI/CD | GitHub Actions |
| 测试 | pytest + 竞赛 e2e（真实 API） |
| 监控 | EventLog + SSE Dashboard |

---

## 二-2、小组成员各自负责部分信息

### 戴尚好 — 全栈 / Agent / 部署

#### 核心负责：Multi-Agent Pipeline 架构 + 全栈实现

**Demo 展示要点**：

1. **Multi-Agent Pipeline 完整实现**
   - 设计并实现 6 Agent 协作架构（Intent/Planner/Research/Writer/Review/Builder）
   - 每个 Agent 有独立的 system prompt、工具集、验证标准
   - Pipeline 编排层（`pipeline.py`）支持 doc/ppt/trio 三种流水线

2. **MiniMax LLM 深度集成**
   - Tool calling 联网搜索（模型自主决策搜索意图）
   - `_strip_thinking` 清理 MiniMax 内部标记
   - Circuit Breaker + 指数退避重试

3. **飞书 Bot 全功能开发**
   - WebSocket 长连接（lark-oapi）
   - CardKit 交互卡片（任务启动/大纲确认/任务交付/主动澄清）
   - Doc API 写入文档 + Drive API 文件管理

4. **Dashboard + MCP Server**
   - FastAPI + SSE 实时推送 Agent 事件
   - 反向 MCP Server 供 Cursor/Claude Desktop 接入

5. **部署与运维**
   - systemd 服务管理 + nginx 反代 + UFW 防火墙
   - GitHub Actions CI/CD
   - 真实 API e2e 测试（14/14 通过）

**核心代码片段**：

```python
# 6 Agent Pipeline 核心编排逻辑
async def doc_pipeline(state: AgentState) -> AgentState:
    state = await PlannerAgent().safe_execute(state)
    state = await ResearchAgent().safe_execute(state)
    for i in range(MAX_REVIEW_ITERATIONS):
        state = await WriterAgent().safe_execute(state)
        state = await ReviewAgent().safe_execute(state)
        if state.get("review_pass"):
            break
    state = await BuilderAgent().safe_execute(state)
    return state
```

### 李洁盈 — 产品 / 设计

#### 核心负责：产品设计 + UI/UX + 用户体验

**Demo 展示要点**：

1. **产品定位与需求分析**
   - "Agent 是主驾驶，GUI 是仪表盘"理念落地
   - 用户旅程地图设计（从需求产生到成果交付）
   - 竞品分析（Coze/Dify/传统 Bot 对比矩阵）

2. **飞书 Bot 交互设计**
   - 对话 UX 流程设计（自然语言触发 → 进度反馈 → 结果交付）
   - CardKit 卡片 UI 设计（视觉层次、信息密度、操作引导）
   - 主动澄清机制设计（模糊意图时如何引导用户）

3. **Dashboard 界面设计**
   - 三段式布局（Result / Detail / Tracing）
   - 配色方案（飞书蓝 + 状态色系）
   - Agent 协作过程可视化设计

4. **产品宣传与内容**
   - 产品介绍网页设计（信息架构、视觉风格）
   - 文案策划（一句话 pitch、场景描述）
   - 演示视频脚本

---

## 三、其他信息（自由发挥区）

### 项目完整性验证

**PRD 要求对照表**（全部通过）：

| PRD 场景 | 要求 | 实现状态 | 测试结果 |
|----------|------|----------|----------|
| 场景 A：意图入口 | IM 文本触发，自然语言理解 | IntentAgent 分类 | PASS |
| 场景 B：任务规划 | LLM 拆解为可执行子任务 | PlannerAgent 大纲 | PASS（7 章） |
| 场景 C：文档生成 | 自动生成并迭代文档 | WriterAgent + ReviewAgent | PASS（5646 字） |
| 场景 D：PPT 生成 | 结构化演示材料 | BuilderAgent + python-pptx | PASS（8 页） |
| 场景 E：多端协同 | 实时同步状态 | Dashboard SSE + Flutter | PASS |
| 场景 F：总结交付 | 汇报/归档成果 | task_delivered_card | PASS |
| 加分：主动澄清 | Agent 发起任务澄清 | IntentAgent clarify | PASS |
| 加分：第三方集成 | 飞书开放平台 API | lark-oapi 全套 | PASS |

### 相关链接汇总

| 资源 | 链接 |
|------|------|
| GitHub 仓库 | https://github.com/bcefghj/Agent-Pilot |
| 在线 Demo | http://8.136.98.175/demo |
| Dashboard | http://8.136.98.175/dashboard |
| 技术白皮书 PDF | http://8.136.98.175/agent_pilot_report.pdf |
| MCP Server | http://8.136.98.175/sse |

---

*Agent-Pilot · 从 IM 对话到演示稿的一键智能闭环*
*2026 飞书 AI 校园挑战赛 · 复赛提交*
*戴尚好 & 李洁盈*
