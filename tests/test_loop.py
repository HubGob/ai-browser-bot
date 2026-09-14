"""Integration-ish test for AILoop with a mocked LLM."""

import json

import httpx
import pytest

from ai_browser_bot.driver import BrowserDriver
from ai_browser_bot.llm import OpenAICompatibleClient
from ai_browser_bot.loop import AILoop


def openai_wrap(content: str) -> dict:
    """Wrap a message content string in the OpenAI chat completions response format."""
    return {
        "id": "m",
        "model": "test",
        "choices": [
            {
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
    }


@pytest.mark.asyncio
async def test_loop_navigates_and_finishes():
    """LLM says navigate to example.com and mark done."""
    action_json = json.dumps({
        "action": {"type": "navigate", "target": "https://example.com"},
        "reasoning": "Go to example.com",
        "done": True,
    })

    def handler(request):
        # Verify the system prompt was sent
        body = json.loads(request.content.decode())
        assert body["messages"][0]["role"] == "system"
        return httpx.Response(
            status_code=200,
            content=json.dumps(openai_wrap(action_json)).encode(),
            headers={"content-type": "application/json"},
        )

    transport = httpx.MockTransport(handler)
    llm = OpenAICompatibleClient(
        base_url="http://mock.local",
        api_key="sk-x",
        http_client=httpx.AsyncClient(transport=transport),
    )
    driver = BrowserDriver()
    await driver.start(headless=True)
    try:
        loop = AILoop(driver, llm, task="Go to example.com", max_steps=5)
        result = await loop.run()
        assert result["status"] == "done"
        assert result["step"] == 1
        title = await driver.page.title()
        assert title == "Example Domain"
    finally:
        await driver.stop()
        await llm.close()


@pytest.mark.asyncio
async def test_loop_errors_on_bad_llm_response():
    """LLM returns malformed JSON inside the OpenAI envelope."""
    def handler(request):
        return httpx.Response(
            status_code=200,
            content=json.dumps(openai_wrap("not json")).encode(),
            headers={"content-type": "application/json"},
        )

    transport = httpx.MockTransport(handler)
    llm = OpenAICompatibleClient(
        base_url="http://mock.local",
        api_key="sk-x",
        http_client=httpx.AsyncClient(transport=transport),
    )
    driver = BrowserDriver()
    await driver.start(headless=True)
    try:
        loop = AILoop(driver, llm, task="do something", max_steps=3)
        result = await loop.run()
        assert result["status"] == "parse_error"
    finally:
        await driver.stop()
        await llm.close()


@pytest.mark.asyncio
async def test_loop_stops_at_max_steps():
    """LLM keeps returning non-done actions; loop hits max_steps."""
    action_json = json.dumps({
        "action": {"type": "wait", "wait_seconds": 0.01},
        "reasoning": "waiting",
        "done": False,
    })

    def handler(request):
        return httpx.Response(
            status_code=200,
            content=json.dumps(openai_wrap(action_json)).encode(),
            headers={"content-type": "application/json"},
        )

    transport = httpx.MockTransport(handler)
    llm = OpenAICompatibleClient(
        base_url="http://mock.local",
        api_key="sk-x",
        http_client=httpx.AsyncClient(transport=transport),
    )
    driver = BrowserDriver()
    await driver.start(headless=True)
    try:
        loop = AILoop(driver, llm, task="wait forever", max_steps=3)
        result = await loop.run()
        assert result["status"] == "max_steps_reached"
        assert result["step"] == 3
    finally:
        await driver.stop()
        await llm.close()
