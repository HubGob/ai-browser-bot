"""Tests for LLMClient — uses a mocked HTTP layer."""

import json

import httpx
import pytest

from ai_browser_bot.llm import OpenAICompatibleClient


def openai_wrap(content: str, model: str = "gpt-4o-mini") -> dict:
    """Wrap a message content string in the OpenAI chat completions response format."""
    return {
        "id": "msg_001",
        "object": "chat.completion",
        "model": model,
        "choices": [
            {
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
    }


@pytest.fixture
def mock_llm():
    """An LLM client backed by a mock transport."""
    response_json = openai_wrap("Hello!")
    transport = httpx.MockTransport(
        lambda req: httpx.Response(
            status_code=200,
            content=json.dumps(response_json).encode(),
            headers={"content-type": "application/json"},
        )
    )
    client = OpenAICompatibleClient(
        base_url="http://mock.local",
        api_key="sk-mock",
        http_client=httpx.AsyncClient(transport=transport),
    )
    return client


@pytest.mark.asyncio
async def test_chat_success(mock_llm):
    result = await mock_llm.chat(
        messages=[{"role": "user", "content": "Hi"}]
    )
    assert result["role"] == "assistant"
    assert result["content"] == "Hello!"


@pytest.mark.asyncio
async def test_chat_with_system_prompt(mock_llm):
    result = await mock_llm.chat(
        messages=[
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hi"},
        ]
    )
    assert result["content"] == "Hello!"


@pytest.mark.asyncio
async def test_chat_error_handling():
    transport = httpx.MockTransport(
        lambda req: httpx.Response(
            status_code=401,
            content=json.dumps({
                "error": {"message": "invalid key", "type": "auth"}
            }).encode(),
            headers={"content-type": "application/json"},
        )
    )
    client = OpenAICompatibleClient(
        base_url="http://mock.local",
        api_key="bad-key",
        http_client=httpx.AsyncClient(transport=transport),
    )
    result = await client.chat(messages=[{"role": "user", "content": "Hi"}])
    assert "error" in result
