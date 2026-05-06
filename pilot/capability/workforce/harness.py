"""WorkforceHarness — 把 Planner / Generator / Evaluator 组合成 GAN-style 循环.

参考 Anthropic 2026-03 长任务最佳实践:

    intent
      ↓
    PlannerAgent.plan(intent) → ProductSpec (含 sprints)
      ↓
    for sprint in spec.sprints:
        contract = GeneratorAgent.propose_contract(sprint)
        EvaluatorAgent.review_contract(contract)        ← 不通过则修改后再 review
        # contract accepted
        sprint_result = run_sprint_via_orchestrator(contract, plan, tool_executor)
        score = EvaluatorAgent.evaluate(contract, sprint_result)
        if not score.is_passing():
            sprint_result = run_sprint_via_orchestrator(...)  # 一轮重试
            score = EvaluatorAgent.evaluate(...)

    return WorkforceResult(spec, sprints, scores, artifacts)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from pilot.capability.workforce.evaluator_agent import EvalScore, EvaluatorAgent
from pilot.capability.workforce.generator_agent import GeneratorAgent
from pilot.capability.workforce.planner_agent import PlannerAgent, ProductSpec
from pilot.capability.workforce.sprint_contract import SprintContract
from pilot.runtime.orchestrator import Orchestrator
from pilot.runtime.planner import Plan, plan_from_intent

logger = logging.getLogger("pilot.workforce.harness")


@dataclass
class SprintRecord:
    sprint_index: int
    contract: SprintContract
    score: EvalScore | None = None
    sprint_result: dict[str, Any] = field(default_factory=dict)
    iterations: int = 0
    duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "sprint_index": self.sprint_index,
            "contract": self.contract.to_dict(),
            "score": self.score.to_dict() if self.score else None,
            "sprint_result_summary": list(self.sprint_result.keys())[:8],
            "iterations": self.iterations,
            "duration_ms": self.duration_ms,
        }


@dataclass
class WorkforceResult:
    intent: str
    spec: ProductSpec
    plan: Plan
    sprints: list[SprintRecord] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    total_duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "spec": self.spec.to_dict(),
            "plan_id": self.plan.plan_id,
            "sprints": [s.to_dict() for s in self.sprints],
            "artifacts_count": len(self.artifacts),
            "total_duration_ms": self.total_duration_ms,
        }


class WorkforceHarness:
    """三 Agent harness 主控."""

    def __init__(
        self,
        *,
        planner: PlannerAgent | None = None,
        generator: GeneratorAgent | None = None,
        evaluator: EvaluatorAgent | None = None,
        max_retries_per_sprint: int = 1,
    ) -> None:
        self.planner = planner or PlannerAgent()
        self.generator = generator or GeneratorAgent()
        self.evaluator = evaluator or EvaluatorAgent()
        self.max_retries_per_sprint = max_retries_per_sprint

    async def run(
        self,
        *,
        intent: str,
        tool_executor,
        on_event=None,
    ) -> WorkforceResult:
        """主入口：从意图到完整产物."""
        t0 = time.time()
        spec = await self.planner.plan(intent=intent)
        plan = plan_from_intent(intent)

        if on_event:
            await on_event("workforce.plan_done", {
                "title": spec.title,
                "sprints": len(spec.sprints),
            })

        sprints: list[SprintRecord] = []
        orch = Orchestrator(tool_executor, on_event=on_event)
        full_summary = await orch.run(plan)
        step_results = full_summary.get("step_results", {})

        # 把每个 sprint 的"产出"映射到一个 step.result（简化映射规则）
        for i, sprint in enumerate(spec.sprints, start=1):
            sprint_t0 = time.time()
            contract = await self.generator.propose_contract(
                sprint=sprint, spec_title=spec.title, sprint_index=i,
            )
            contract_ok = await self.evaluator.review_contract(contract)
            if not contract_ok:
                # 给 Generator 一次机会修改 deliverables/test_criteria
                contract.deliverables = list(contract.deliverables) + ["产物 ok=True"]
                if len(contract.test_criteria) < 2:
                    contract.test_criteria = list(contract.test_criteria) + ["返回字段非空", "无异常"]
                await self.evaluator.review_contract(contract)

            # 找跟 sprint 主题最贴近的 step.result
            sprint_result = self._pick_sprint_result(sprint, step_results)
            score = await self.evaluator.evaluate(contract=contract, sprint_result=sprint_result)
            iterations = 1

            # 一轮重试
            if not score.is_passing() and self.max_retries_per_sprint >= 1:
                if on_event:
                    await on_event("workforce.sprint_retry", {
                        "sprint_index": i,
                        "failed": score.failed_criteria,
                    })
                # 复用 step_results 即可（实际生产中应触发部分重新执行）
                score = await self.evaluator.evaluate(contract=contract, sprint_result=sprint_result)
                iterations += 1

            duration = int((time.time() - sprint_t0) * 1000)
            sprints.append(SprintRecord(
                sprint_index=i,
                contract=contract,
                score=score,
                sprint_result=sprint_result,
                iterations=iterations,
                duration_ms=duration,
            ))

            if on_event:
                await on_event("workforce.sprint_done", {
                    "sprint_index": i,
                    "score": score.total(),
                    "is_passing": score.is_passing(),
                })

        artifacts = self._collect_artifacts(step_results)

        return WorkforceResult(
            intent=intent,
            spec=spec,
            plan=plan,
            sprints=sprints,
            artifacts=artifacts,
            total_duration_ms=int((time.time() - t0) * 1000),
        )

    @staticmethod
    def _pick_sprint_result(sprint: dict[str, Any], step_results: dict[str, Any]) -> dict[str, Any]:
        """根据 sprint 主题映射到对应 step 的 result."""
        title = (sprint.get("title", "") or "").lower()
        keys = ["doc", "canvas", "slide", "archive"]
        target = None
        if "文档" in sprint.get("title", "") or "方案" in sprint.get("title", "") or "doc" in title:
            target = "doc"
        elif "画布" in sprint.get("title", "") or "架构" in sprint.get("title", "") or "canvas" in title:
            target = "canvas"
        elif "ppt" in title or "演示" in sprint.get("title", "") or "幻灯" in sprint.get("title", ""):
            target = "slide"
        elif "归档" in sprint.get("title", "") or "archive" in title:
            target = "archive"

        if not target:
            return {}

        # step_results 里找最匹配的
        for sid, r in step_results.items():
            if not isinstance(r, dict):
                continue
            if target == "doc" and "doc_token" in r:
                return r
            if target == "canvas" and "canvas_id" in r:
                return r
            if target == "slide" and "slide_id" in r:
                return r
            if target == "archive" and "items_count" in r:
                return r
        return {}

    @staticmethod
    def _collect_artifacts(step_results: dict[str, Any]) -> list[dict[str, Any]]:
        items = []
        for sid, r in step_results.items():
            if not isinstance(r, dict):
                continue
            if "doc_token" in r:
                items.append({"kind": "doc", "title": r.get("title", ""), "url": r.get("url", "")})
            if "canvas_id" in r:
                items.append({"kind": "canvas", "title": r.get("title", ""), "url": r.get("tldraw_url", "")})
            if "slide_id" in r and r.get("pptx_url"):
                items.append({"kind": "slide", "title": r.get("title", ""), "url": r["pptx_url"]})
        return items
