#!/usr/bin/env python3
"""裁判级 Demo 脚本 — 跑 5 条 e2e 用例，生成 HTML 报告.

用法:
    python scripts/judge_demo.py            # mocked LLM
    python scripts/judge_demo.py --real     # 真 LLM（需 API key）
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pilot.capability.tools.registry import default_registry
from pilot.runtime.orchestrator import Orchestrator
from pilot.runtime.planner import plan_from_intent

REPORT_DIR = ROOT / "data" / "test_reports"


SCENARIOS = [
    {"id": "short_doc", "title": "1. 文档生成",
     "intent": "帮我写一份关于 AI Agent 发展趋势的报告"},
    {"id": "three_in_one", "title": "2. 三件套 (doc + canvas + slide)",
     "intent": "产品方案 + 架构图 + 评审 PPT"},
    {"id": "canvas_only", "title": "3. 单画布",
     "intent": "画一张产品架构图"},
    {"id": "ppt_only", "title": "4. 单 PPT",
     "intent": "做一份 8 页客户汇报 PPT"},
    {"id": "voice_input", "title": "5. 语音输入流程",
     "intent": "（mock 语音转文字）帮我写一份周报"},
]


async def run_one(scenario: dict) -> dict:
    """跑一个场景，返回结果."""
    t0 = time.time()
    plan = plan_from_intent(scenario["intent"])
    reg = default_registry()
    orch = Orchestrator(reg)
    summary = await orch.run(plan)
    elapsed = time.time() - t0

    artifacts = []
    for s in plan.steps:
        if s.tool == "doc.create" and s.result.get("doc_token"):
            artifacts.append({"kind": "doc", "url": s.result.get("url", "")})
        if s.tool == "canvas.create" and s.result.get("canvas_id"):
            artifacts.append({"kind": "canvas", "mermaid": s.result.get("mermaid", "")[:200]})
        if s.tool == "slide.generate" and s.result.get("slide_id"):
            artifacts.append({"kind": "slide", "pptx": s.result.get("pptx_url", ""), "pages": s.result.get("pages", 0)})

    return {
        "id": scenario["id"],
        "title": scenario["title"],
        "intent": scenario["intent"],
        "plan_id": plan.plan_id,
        "steps": [s.to_dict() for s in plan.steps],
        "completed_count": len(summary.get("completed", [])),
        "failed_count": len(summary.get("failed", [])),
        "elapsed_sec": round(elapsed, 2),
        "artifacts": artifacts,
        "ok": len(summary.get("failed", [])) == 0,
    }


async def main():
    real = "--real" in sys.argv

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_dir = REPORT_DIR / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    if not real:
        os.environ.pop("ANTHROPIC_API_KEY", None)
        os.environ.pop("MINIMAX_API_KEY", None)
        os.environ.pop("DOUBAO_API_KEY", None)

    print(f"==> 报告将输出到: {out_dir}")
    print(f"==> 模式: {'real LLM' if real else 'mocked LLM'}")
    print()

    results = []
    for scenario in SCENARIOS:
        print(f"  ▶ {scenario['title']}")
        try:
            r = await run_one(scenario)
            print(f"    {'✓' if r['ok'] else '✗'} {r['completed_count']}/{r['completed_count'] + r['failed_count']} 步完成 · {r['elapsed_sec']}s")
            results.append(r)
        except Exception as e:
            print(f"    ✗ 异常: {e}")
            results.append({"id": scenario["id"], "title": scenario["title"], "ok": False, "error": str(e)})

    # 写 JSON
    (out_dir / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    # 写 HTML
    html = _render_html(results, ts, real)
    (out_dir / "index.html").write_text(html, encoding="utf-8")

    print()
    print(f"==> 报告: {out_dir / 'index.html'}")
    passed = sum(1 for r in results if r.get("ok"))
    print(f"==> {passed}/{len(results)} passed")


def _render_html(results: list, ts: str, real: bool) -> str:
    rows = []
    for r in results:
        status = "✅" if r.get("ok") else "❌"
        steps_html = ""
        for s in (r.get("steps") or []):
            steps_html += f'<li><code>{s["tool"]}</code> · {s["description"]} · <span class="status-{s["status"]}">{s["status"]}</span></li>'
        artifacts_html = ""
        for a in (r.get("artifacts") or []):
            kind = a.get("kind", "")
            if kind == "doc":
                artifacts_html += f'<div class="art">📄 <a href="{a.get("url", "#")}">飞书文档</a></div>'
            elif kind == "canvas":
                artifacts_html += f'<div class="art">🎨 画布<br><pre>{a.get("mermaid", "")[:120]}</pre></div>'
            elif kind == "slide":
                artifacts_html += f'<div class="art">📊 PPT · {a.get("pages")} 页 · <a href="{a.get("pptx", "")}">下载</a></div>'

        rows.append(f"""
<section class="card">
  <h2>{status} {r.get('title', '')}</h2>
  <p class="intent"><b>意图:</b> {r.get('intent', '')}</p>
  <p class="meta">{r.get('completed_count', 0)}/{r.get('completed_count', 0) + r.get('failed_count', 0)} 步完成 · {r.get('elapsed_sec', 0)}s · plan_id: <code>{r.get('plan_id', '')[:24]}</code></p>
  <details><summary>步骤详情</summary><ol>{steps_html}</ol></details>
  <div class="artifacts">{artifacts_html}</div>
</section>""")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<title>Agent-Pilot V1 · 裁判 Demo 报告 {ts}</title>
<style>
body {{ font-family: -apple-system, "PingFang SC", sans-serif; max-width: 1100px; margin: 30px auto; padding: 0 20px; color: #1f2937; }}
h1 {{ background: linear-gradient(135deg, #6366f1, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
.card {{ background: #f9fafb; border-radius: 12px; padding: 18px; margin: 16px 0; border: 1px solid #e5e7eb; }}
.intent {{ color: #6b7280; }}
.meta {{ color: #9ca3af; font-size: 13px; }}
.status-done {{ color: #10b981; font-weight: bold; }}
.status-failed {{ color: #ef4444; }}
.status-pending {{ color: #6b7280; }}
.artifacts {{ display: flex; gap: 10px; margin-top: 10px; flex-wrap: wrap; }}
.art {{ background: white; padding: 12px; border-radius: 8px; border: 1px solid #e5e7eb; min-width: 200px; }}
code {{ background: #f3f4f6; padding: 2px 6px; border-radius: 4px; font-size: 13px; }}
pre {{ font-size: 11px; overflow-x: auto; max-height: 80px; }}
ol li {{ padding: 4px 0; }}
</style>
</head>
<body>
<h1>🛫 Agent-Pilot V1 · 裁判 Demo 报告</h1>
<p>生成时间: {ts} · 模式: <b>{'real LLM' if real else 'mocked LLM'}</b></p>
<p>{sum(1 for r in results if r.get('ok'))}/{len(results)} 用例通过</p>
{''.join(rows)}
</body></html>"""


if __name__ == "__main__":
    asyncio.run(main())
