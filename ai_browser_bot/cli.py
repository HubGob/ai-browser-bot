"""Command-line entry point for the AI browser bot."""

from __future__ import annotations

import argparse
import os
import sys

import anyio
from dotenv import load_dotenv

# Load environment variables from a .env file at import time so that
# secrets and provider configuration are available before any other
# module reads them.
load_dotenv()

from ai_browser_bot.driver import BrowserDriver
from ai_browser_bot.llm import OpenAICompatibleClient
from ai_browser_bot.loop import AILoop


def _resolve_api_key(explicit: str | None, llm_url: str) -> str:
    """Resolve the API key from explicit flag, then env vars.

    Supports both OPENAI_API_KEY (the conventional name) and LLM_API_KEY
    (a provider-agnostic alternative). For OpenAI's hosted API a key is
    required; for self-hosted / local OpenAI-compatible servers the key
    is optional.
    """
    if explicit:
        return explicit
    return os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY") or ""


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="ai-bot",
        description="AI browser automation from scratch",
    )
    p.add_argument("task", help="Natural-language task for the bot to perform")
    p.add_argument(
        "--llm-url",
        default="https://api.openai.com/v1",
        help="OpenAI-compatible API base URL (default: OpenAI)",
    )
    p.add_argument(
        "--llm-model",
        default="gpt-4o-mini",
        help="Model name (default: gpt-4o-mini)",
    )
    p.add_argument(
        "--api-key",
        default=None,
        help="API key (default: reads OPENAI_API_KEY or LLM_API_KEY env var)",
    )
    p.add_argument(
        "--max-steps",
        type=int,
        default=20,
        help="Maximum loop iterations (default: 20)",
    )
    p.add_argument(
        "--headed",
        action="store_true",
        help="Show the browser window instead of headless",
    )
    p.add_argument(
        "--viewer",
        action="store_true",
        help="Write run_state.json + screenshot.png each step for the viewer",
    )
    return p.parse_args(args)


async def _run(args: argparse.Namespace) -> int:
    api_key = _resolve_api_key(args.api_key, args.llm_url)
    # Only require a key for OpenAI's own API. For self-hosted or local
    # OpenAI-compatible servers, most don't need a key at all.
    if not api_key and "openai.com" in args.llm_url:
        print(
            "Error: no API key provided. Set --api-key or OPENAI_API_KEY "
            "or LLM_API_KEY in your environment or .env file.",
            file=sys.stderr,
        )
        return 1

    driver = BrowserDriver()
    llm = OpenAICompatibleClient(
        base_url=args.llm_url,
        api_key=api_key,
        model=args.llm_model,
    )

    try:
        await driver.start(headless=not args.headed)
        loop = AILoop(
            driver=driver,
            llm=llm,
            task=args.task,
            max_steps=args.max_steps,
            write_viewer_state=args.viewer,
        )
        result = await loop.run()
    finally:
        await driver.stop()
        await llm.close()

    # Report
    status = result.get("status", "unknown")
    step = result.get("step", "?")
    print("\n=== Result ===")
    print(f"Status: {status}")
    print(f"Step: {step}")
    if "reasoning" in result:
        print(f"Reasoning: {result['reasoning']}")
    if "last_result" in result:
        print(f"Last action: {result['last_result']}")
    if status == "error":
        print(f"Error: {result.get('error')}")
        return 1
    if status == "parse_error":
        print(f"Parse error: {result.get('error')}")
        return 1
    return 0


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    exit_code = anyio.run(_run, args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
