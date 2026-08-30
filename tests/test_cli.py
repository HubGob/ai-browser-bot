"""Tests for CLI argument parsing."""

import pytest
from ai_browser_bot.cli import parse_args


def test_default_args():
    ns = parse_args(["go to example.com"])
    assert ns.task == "go to example.com"
    assert ns.llm_url == "https://api.openai.com/v1"
    assert ns.llm_model == "gpt-4o-mini"
    assert ns.api_key is None
    assert ns.max_steps == 20
    assert ns.headed is False


def test_custom_args():
    ns = parse_args([
        "search for cats",
        "--llm-url", "http://localhost:8080/v1",
        "--llm-model", "local-model",
        "--api-key", "sk-test",
        "--max-steps", "10",
        "--headed",
    ])
    assert ns.task == "search for cats"
    assert ns.llm_url == "http://localhost:8080/v1"
    assert ns.llm_model == "local-model"
    assert ns.api_key == "sk-test"
    assert ns.max_steps == 10
    assert ns.headed is True
