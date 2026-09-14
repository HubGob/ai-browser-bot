"""Tests for failure / safety paths.

These cover scenarios that should degrade gracefully instead of raising
exceptions or performing unsafe actions:
  - malformed/empty LLM output does not crash the loop
  - javascript: URIs are blocked by the safety policy
  - running the CLI without an API key against OpenAI's hosted API exits
    non-zero with a clear error message
"""

import json
from unittest import mock

import httpx
import pytest

from ai_browser_bot.llm import OpenAICompatibleClient
from ai_browser_bot.loop import AILoop
from ai_browser_bot.safety import SafetyPolicy


def _wrap(content: str) -> dict:
    """Build an OpenAI-style chat completion response with `content`."""
    return {
        "id": "test",
        "model": "test",
        "choices": [
            {
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
    }


def _make_llm(content: str) -> OpenAICompatibleClient:
    transport = httpx.MockTransport(
        lambda req: httpx.Response(
            status_code=200,
            content=json.dumps(_wrap(content)).encode(),
            headers={"content-type": "application/json"},
        )
    )
    return OpenAICompatibleClient(
        base_url="http://mock.local",
        api_key="sk-x",
        http_client=httpx.AsyncClient(transport=transport),
    )


def _make_stubbed_loop(llm: OpenAICompatibleClient, max_steps: int = 3) -> AILoop:
    """Build an AILoop whose inspector and executor are stubbed out."""
    loop = AILoop(driver=mock.Mock(), llm=llm, task="do a thing", max_steps=max_steps)
    loop.inspector = mock.Mock()
    loop.inspector.snapshot = mock.AsyncMock(return_value="fake snapshot")
    return loop


# ---------------------------------------------------------------------------
# (a) Malformed / empty LLM output -> loop returns an error dict, not a raise
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_malformed_llm_output_does_not_raise():
    """Garbage (non-JSON) content is caught and reported, not raised."""
    llm = _make_llm("not valid json at all {{{")
    loop = _make_stubbed_loop(llm)

    result = await loop.run()
    assert isinstance(result, dict)
    assert result["status"] in ("error", "parse_error")
    assert "error" in result
    await llm.close()


@pytest.mark.asyncio
async def test_empty_llm_output_does_not_raise():
    """Empty content is unparseable JSON; the loop must not raise."""
    llm = _make_llm("")
    loop = _make_stubbed_loop(llm)

    result = await loop.run()
    assert isinstance(result, dict)
    # json.loads("") raises JSONDecodeError -> caught -> parse_error
    assert result["status"] in ("error", "parse_error")
    assert "error" in result
    await llm.close()


# ---------------------------------------------------------------------------
# (b) A blocked action (javascript: URI) is refused by SafetyPolicy.check()
# ---------------------------------------------------------------------------

def test_javascript_uri_blocked_by_safety():
    """Navigating to a javascript: URI must be refused."""
    policy = SafetyPolicy()
    action = {"type": "navigate", "target": "javascript:alert(document.cookie)"}
    violation = policy.check(action)
    assert violation is not None
    assert isinstance(violation, str)
    assert "javascript" in violation.lower()


@pytest.mark.asyncio
async def test_loop_refuses_blocked_action():
    """The loop skips a blocked action (javascript: navigate), never executes it."""
    action_json = json.dumps(
        {
            "action": {"type": "navigate", "target": "javascript:alert(1)"},
            "reasoning": "trying to be sneaky",
            "done": False,
        }
    )
    llm = _make_llm(action_json)
    loop = _make_stubbed_loop(llm, max_steps=2)

    # The executor must never be called because safety blocks first.
    with mock.patch.object(
        loop.executor, "execute", new_callable=mock.AsyncMock
    ) as exec_mock:
        result = await loop.run()

    assert exec_mock.call_count == 0
    # Two iterations both hit the blocked-action path; loop hits max_steps.
    assert result["status"] == "max_steps_reached"
    await llm.close()


# ---------------------------------------------------------------------------
# (c) No API key + OpenAI base URL -> CLI exits non-zero + prints key error
# ---------------------------------------------------------------------------

def test_cli_exits_without_api_key(capsys):
    """With no key set and an OpenAI URL, main() must exit non-zero."""
    from ai_browser_bot import cli

    argv = [
        "go to example.com",
        "--llm-url",
        "https://api.openai.com/v1",
        "--api-key",
        "",
    ]
    # Ensure neither key is present in the environment.
    clean_env = {
        k: v
        for k, v in __import__("os").environ.items()
        if k not in ("OPENAI_API_KEY", "LLM_API_KEY")
    }
    with mock.patch.dict("os.environ", clean_env, clear=True):
        with pytest.raises(SystemExit) as exc_info:
            cli.main(argv)

    assert exc_info.value.code != 0
    err = capsys.readouterr().err
    assert "api key" in err.lower() or "OPENAI_API_KEY" in err
