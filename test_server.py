#!/usr/bin/env python3
"""Server-side test script for Agent-Pilot core functions."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

def test_llm():
    print("=== Test 1: LLM Chat ===")
    from llm.llm_client import chat as llm_chat
    reply = llm_chat("请用markdown格式写一段关于人工智能发展趋势的简短文档，包括标题和3个小节。控制在300字以内。")
    print(f"LLM reply length: {len(reply) if reply else 0}")
    if reply:
        print(f"Content preview: {reply[:400]}")
    else:
        print("ERROR: LLM returned empty reply!")
    return reply

def test_blocks(md_text):
    print("\n=== Test 2: Markdown to Blocks ===")
    from core.agent_pilot.tools.doc_tool import _markdown_to_blocks
    if not md_text:
        md_text = "# AI\n\n## Deep Learning\n\n- LLM\n- Multimodal\n\n## Apps\n\n- Office\n- Auto"
    blocks = _markdown_to_blocks(md_text)
    print(f"Blocks count: {len(blocks)}")
    for i, b in enumerate(blocks[:5]):
        bt = getattr(b, "block_type", "?")
        print(f"  block[{i}]: block_type={bt}")
    return blocks

def test_doc_create():
    print("\n=== Test 3: Feishu Doc Create ===")
    from bot.feishu_client import get_client
    from lark_oapi.api.docx.v1 import CreateDocumentRequest, CreateDocumentRequestBody
    client = get_client()
    req = (
        CreateDocumentRequest.builder()
        .request_body(CreateDocumentRequestBody.builder().title("[Test] AI Development Trends").build())
        .build()
    )
    resp = client.docx.v1.document.create(req)
    if resp.success():
        doc = resp.data.document
        token = doc.document_id
        url = f"https://rcnqvnspd31b.feishu.cn/docx/{token}"
        print(f"Doc created: token={token} url={url}")
        return token
    else:
        print(f"Doc create FAILED: code={resp.code} msg={resp.msg}")
        return None

def test_doc_append(token, md_text):
    print("\n=== Test 4: Feishu Doc Append ===")
    from core.agent_pilot.tools.doc_tool import _try_append_feishu_blocks
    if not md_text:
        md_text = "# AI Trends\n\n## Section 1\n\nContent here.\n\n- Point 1\n- Point 2"
    count = _try_append_feishu_blocks(token, md_text)
    print(f"Blocks appended: {count}")
    return count

if __name__ == "__main__":
    md = test_llm()
    blocks = test_blocks(md)
    token = test_doc_create()
    if token:
        count = test_doc_append(token, md)
        print(f"\n=== RESULT ===")
        print(f"LLM content: {'OK' if md else 'FAIL'} ({len(md) if md else 0} chars)")
        print(f"Block convert: {'OK' if blocks else 'FAIL'} ({len(blocks)} blocks)")
        print(f"Doc create: OK (token={token})")
        print(f"Doc append: {'OK' if count > 0 else 'FAIL'} ({count} blocks written)")
    else:
        print("\n=== RESULT: Doc creation failed, cannot test append ===")
