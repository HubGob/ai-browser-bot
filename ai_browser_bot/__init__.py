"""AI Browser Bot — from-scratch browser automation with Playwright + LLM."""

from __future__ import annotations

from ai_browser_bot.driver import BrowserDriver
from ai_browser_bot.dom import DOMInspector
from ai_browser_bot.actions import Action, ActionExecutor
from ai_browser_bot.llm import LLMClient, OpenAICompatibleClient
from ai_browser_bot.loop import AILoop
from ai_browser_bot.safety import SafetyPolicy
from ai_browser_bot.memory import SessionMemory

__all__ = [
    "BrowserDriver",
    "DOMInspector",
    "Action",
    "ActionExecutor",
    "LLMClient",
    "OpenAICompatibleClient",
    "AILoop",
    "SafetyPolicy",
    "SessionMemory",
]
