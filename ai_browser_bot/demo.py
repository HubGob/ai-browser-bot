"""End-to-end demo — navigates to example.com and reports.

This demonstrates the full stack: driver → DOM inspector → action
executor → LLM (mocked for the demo) → AI loop.

To run with a real LLM, set OPENAI_API_KEY and use --real.
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any, Dict

import httpx

from ai_browser_bot.driver import BrowserDriver
from ai_browser_bot.llm import OpenAICompatibleClient
from ai_browser_bot.loop import AILoop


async def demo_with_mock_llm() -> None:
    """Run the loop with a canned LLM response — no API key needed."""

    # The canned response: navigate, then mark done
    canned_content = json.dumps({
        "action": {"type": "navigate", "target": "https://example.com"},
        "reasoning": "Navigate to example.com as requested",
        "done": True,
    })

    def handler(request):
        return httpx.Response(
            status_code=200,
            content=json.dumps({
                "id": "demo",
                "model": "test",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": canned_content,
                        }
                    }
                ],
            }).encode(),
            headers={"content-type": "application/json"},
        )

    llm = OpenAICompatibleClient(
        base_url="http://demo.local",
        api_key="demo",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    driver = BrowserDriver()

    try:
        await driver.start(headless=True)
        loop = AILoop(driver, llm, task="Go to example.com", max_steps=5)
        result = await loop.run()

        print("\n========== Demo Result ==========")
        print(f"Status: {result['status']}")
        print(f"Step:   {result['step']}")
        if result.get("reasoning"):
            print(f"Reasoning: {result['reasoning']}")
        if result.get("last_result"):
            print(f"Last action result: {result['last_result']}")

        if result["status"] == "done":
            title = await driver.page.title()
            print(f"\nPage title: {title}")
            print("✓ Demo succeeded")
        else:
            print(f"\n✗ Demo ended with status: {result['status']}")

    finally:
        await driver.stop()
        await llm.close()


async def demo_with_real_llm(task: str, api_key: str) -> None:
    """Run the loop with a real OpenAI-compatible LLM."""
    llm = OpenAICompatibleClient(
        base_url="https://api.openai.com/v1",
        api_key=api_key,
        model="gpt-4o-mini",
    )
    driver = BrowserDriver()

    try:
        await driver.start(headless=True)
        loop = AILoop(driver, llm, task=task, max_steps=20)
        result = await loop.run()
        print(json.dumps(result, indent=2, default=str))
    finally:
        await driver.stop()
        await llm.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--real":
        if len(sys.argv) < 3:
            print(
                "Usage: demo.py --real 'your task here'",
                file=sys.stderr,
            )
            print("Set OPENAI_API_KEY env var first.", file=sys.stderr)
            sys.exit(1)
        api_key = sys.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            print("OPENAI_API_KEY not set.", file=sys.stderr)
            sys.exit(1)
        asyncio.run(demo_with_real_llm(sys.argv[2], api_key))
    else:
        asyncio.run(demo_with_mock_llm())
