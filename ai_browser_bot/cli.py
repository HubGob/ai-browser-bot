"""Command-line entry point for the AI browser bot."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Optional

import anyio

from ai_browser_bot.driver import BrowserDriver
from ai_browser_bot.llm import OpenAICompatibleClient
from ai_browser_bot.loop import AILoop


def parse_args(args: Optional[list[str]] = None) -> argparse.Namespace:
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
        help="API key (default: reads OPENAI_API_KEY env var)",
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
    return p.parse_args(args)


async def _run(args: argparse.Namespace) -> int:
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY", "")
    # Only require a key for OpenAI's own API. For self-hosted or local
    # OpenAI-compatible servers, most don't need a key at all.
    if not api_key and "openai.com" in args.llm_url:
        print(
            "Error: no API key provided. Set --api-key or OPENAI_API_KEY.",
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
    return 0


def main(argv: Optional[list[str]] = None) -> None:
    args = parse_args(argv)
    exit_code = anyio.run(_run, args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

